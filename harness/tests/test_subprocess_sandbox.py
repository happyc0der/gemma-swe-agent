from pathlib import Path

from swelite.subprocess_sandbox import SubprocessSandbox


def test_root_not_under_tmp_and_rewrite_stable(tmp_path):
    sb = SubprocessSandbox(base_dir=tmp_path)
    assert not str(sb.root).startswith("/tmp/")
    cmd = sb._rewrite("cd /workspace && cat > /tmp/x.py && ls /wheels")
    assert cmd.count(str(sb.root)) == 3 and "/tmp/x.py" not in cmd.replace(str(sb.tmp), "")
    sb.stop()
