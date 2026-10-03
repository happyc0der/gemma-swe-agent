"""Make the official swegemma subprocess sandbox behave like the scorer's Docker sandbox on a Kaggle kernel.

Why: the official `SubprocessManager` (the one the organizers' own Kaggle notebook uses) creates each task venv
from the harness interpreter with `system_site_packages=True` and skips per-task dependency setup. On Kaggle that
means the agent's repro scripts import the image's installed rich/requests/fastapi instead of /workspace, run on
the wrong Python (the competition wheels target cp313, like the scorer's python:3.13-slim image), and lack test
plugins. Our earlier T4 runs showed exactly that (import errors in 24 of 33 tasks).

What `apply()` changes, for both the agent sandbox and the verification sandbox:
- each sandbox venv is created with uv-managed Python 3.13 and pip, without host site-packages;
- the per-task setup installs what the scorer image bakes in (pytest, pytest-timeout 2.1.0, typer, build backends),
  the test-only packages the public wheel set lacks, then runs the dataset's own `sandbox/setup.py` (full path:
  the repo's declared requirements from the competition wheels, editable install of /workspace, workspace .pth,
  pytest.ini/conftest);
- the per-task copy of the 1.7 GB wheel directory is skipped: wheels are read from a host directory linked at /wheels.

`prepare_host()` must run once first (needs internet): installs uv + Python 3.13 and builds the merged wheel dir.
"""
from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("faithful_sandbox")

MERGED = Path("/opt/wheels_merged")       # host path; the sandbox's path rewriting only touches /tmp, /workspace, /wheels, /usr/local/bin
EXTRA = Path("/opt/extra_wheels")
# What python:3.13-slim gets in the scorer's Dockerfile.public.
BASE_PKGS = ["pip", "pytest", "pytest-timeout==2.1.0", "typer", "pdm-backend", "setuptools", "wheel", "poetry-core",
             "hatchling", "flit-core", "editables"]
# Test-only dependencies the public wheel set lacks (same list as swelite's local Docker layer, which took gold to 109/129).
TEST_EXTRAS = ["dirty-equals", "inline-snapshot", "sqlmodel", "flask", "anyio[trio]", "PyJWT", "pyyaml", "passlib[bcrypt]",
               "python-multipart", "email-validator", "jinja2", "orjson", "ujson", "pydantic-settings",
               "pydantic-extra-types", "httpx", "attrs", "pytest-httpbin", "httpbin", "trustme", "PySocks", "chardet",
               "typing-inspection"]
_UV = None
_SETUP_PY: Path | None = None


def _run(cmd: str, timeout: int = 1800) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        log.warning("cmd failed rc=%s: %s\n%s", r.returncode, cmd[:200], (r.stdout + r.stderr)[-1500:])
    return r


def prepare_host(data_dir: Path) -> dict:
    """Install uv + CPython 3.13 and build /opt/wheels_merged = competition wheels + base tools + test extras (cp313)."""
    global _UV, _SETUP_PY
    _run("python3 -m pip install -q uv")
    found = shutil.which("uv") or os.path.expanduser("~/.local/bin/uv")
    Path("/opt/uv").mkdir(parents=True, exist_ok=True)
    shutil.copy(found, "/opt/uv/uv")      # /usr/local/bin paths would be rewritten inside sandbox commands
    _UV = "/opt/uv/uv"
    _run(f"{_UV} python install 3.13")
    EXTRA.mkdir(parents=True, exist_ok=True)
    # Binary wheels for the sandbox interpreter (cp313 manylinux), with dependencies; one package per call so a
    # package without a matching wheel cannot abort the rest.
    failed = []
    for p in BASE_PKGS + TEST_EXTRAS:
        r = _run(f"python3 -m pip download -q --only-binary=:all: --python-version 3.13 --implementation cp "
                 f"--abi cp313 --abi abi3 --abi none --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 "
                 f"--platform manylinux_2_28_x86_64 --platform any -d {EXTRA} {shlex.quote(p)}", timeout=900)
        if r.returncode != 0:
            failed.append(p)
    MERGED.mkdir(parents=True, exist_ok=True)
    for w in list((data_dir / "wheels").glob("*.whl")) + list(EXTRA.glob("*.whl")):
        dst = MERGED / w.name
        if not dst.exists():
            dst.symlink_to(w)
    if Path("/wheels").is_symlink() or not Path("/wheels").exists():
        _run(f"ln -sfn {MERGED} /wheels")   # dataset setup.py hard-codes /wheels in Python, which the sandbox does not rewrite
    _SETUP_PY = data_dir / "sandbox" / "setup.py"
    return {"uv": _UV, "merged_wheels": len(list(MERGED.glob("*.whl"))), "extra_wheels": len(list(EXTRA.glob("*.whl"))),
            "setup_py": str(_SETUP_PY), "python313": _run(f"{_UV} python find 3.13").stdout.strip(), "download_failed": failed}


def _uv_venv_create(env_dir, system_site_packages=False, clear=False, symlinks=False, with_pip=False, prompt=None,
                    upgrade_deps=False, *a, **kw):
    """Drop-in for venv.create used by SubprocessManager.start: a clean CPython 3.13 venv with pip."""
    r = _run(f"{_UV} venv -q --python 3.13 --seed {shlex.quote(str(env_dir))}", timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"uv venv failed: {r.stderr[-500:]}")


def _install_test_dependencies(docker, container_id, repo: str = "", *, fast_path: bool = True, config=None) -> None:
    """Scorer-like per-task environment inside the sandbox venv (python3 resolves to the venv's 3.13)."""
    base = " ".join(shlex.quote(p) for p in BASE_PKGS + TEST_EXTRAS)
    r1 = docker.exec(container_id, f'{_UV} pip install -q --python "$(command -v python3)" --no-index --find-links {MERGED} {base}', timeout=900)
    docker.copy_to(container_id, _SETUP_PY, "/tmp/setup.py")
    r2 = docker.exec(container_id, f"cd /workspace && python3 /tmp/setup.py --no-fast-path --workspace /workspace {repo}", timeout=900)
    if getattr(r1, "exit_code", 0) != 0 or getattr(r2, "exit_code", 0) != 0:
        log.warning("sandbox setup issues for %s: base rc=%s setup rc=%s %s", repo, getattr(r1, "exit_code", "?"),
                    getattr(r2, "exit_code", "?"), (getattr(r2, "stderr", "") or "")[-400:])


def _noop(*a, **kw):
    return None


def apply() -> None:
    """Monkeypatch swegemma so agent and verification sandboxes are scorer-like. Call after prepare_host()."""
    assert _UV and _SETUP_PY, "call prepare_host() first"
    import swegemma.sandbox.subprocess as sp
    import swegemma.harness.container_setup as cs
    import swegemma.harness.agent_runner as ar
    import swegemma.harness.verification as vf

    sp.venv.create = _uv_venv_create
    orig_init = sp.SubprocessManager.__init__

    def init(self, *a, **kw):
        kw["system_site_packages"] = False
        orig_init(self, *a, **kw)
    sp.SubprocessManager.__init__ = init
    for mod in (cs, ar, vf):
        if hasattr(mod, "install_test_dependencies"):
            mod.install_test_dependencies = _install_test_dependencies
        if hasattr(mod, "install_editable_package"):
            mod.install_editable_package = _noop      # setup.py does the editable install with the right backends present
        if hasattr(mod, "setup_container_wheels"):
            mod.setup_container_wheels = _noop        # wheels are read from the host's /opt/wheels_merged
    log.info("faithful sandbox patches applied")
