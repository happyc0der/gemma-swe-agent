"""Compile a submission dir with the OFFICIAL adk-submission/swegemma (wheelhouse) and print the key settings."""
import os, sys, json, yaml
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
from pathlib import Path
from adk_submission import compile_submission, discover_adapters, ToolRegistry
from swegemma.config import build_submission_limits, ALLOWED_ADAPTER_EXTENSIONS, ALLOWED_SUBMISSION_EXTENSIONS
from swegemma.models.registry import setup_gemma_model_registry
from swegemma.context import SwegemmaContext
from swegemma.models import resolve_swegemma_adapter
sub = Path(sys.argv[1])
adapters = discover_adapters(str(sub), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
models = setup_gemma_model_registry(api_base='http://127.0.0.1:8000/v1', served_model='gemma-4-31b-it-qat-w4a16-ct', adapter_manifest=adapters)
limits, gc = build_submission_limits(); ctx = SwegemmaContext(problem_statement='x', task_id='t', repo='r'); tr = ToolRegistry()
for k, v in ctx.create_tools().items(): tr.register(k, v)
a = compile_submission(submission_dir=sub, tool_registry=tr, model_registry=models, limits=limits, generation_constraints=gc,
                       adapter_manifest=adapters, adapter_resolver_fn=lambda b, i: resolve_swegemma_adapter(b, i, models), script_timeout=180)
bad = [str(p) for p in sub.rglob('*') if p.is_file() and not p.name.startswith('.') and p.suffix.lower() not in ALLOWED_SUBMISSION_EXTENSIONS]
print('COMPILE_OK', sub, '| eval', yaml.safe_load(open(sub / 'eval_config.yaml'))['evaluation'],
      '| thinking', json.dumps(a.model._additional_args.get('extra_body')), '| tools', len(a.tools), '| disallowed', bad)
