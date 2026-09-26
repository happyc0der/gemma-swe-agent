"""Scorer-replica probe: ADK 1.36.1 + official swegemma tools against vLLM 0.19.1 serving the real 31B (port 8001).
Prints, for thinking on/off: raw tool calls returned by the server and the argument types the tool receives."""
import asyncio, json, os, sys
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
import litellm
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
seen = []
def read_file(filepath: str, start_line: int | None = None, end_line: int | None = None) -> str:
    """Read the contents of a file from the repository workspace.

    Args:
        filepath: Relative path within the workspace directory.
        start_line: Optional starting line number (1-indexed, inclusive).
        end_line: Optional ending line number (1-indexed, inclusive).
    """
    seen.append(('read_file', repr(start_line), repr(end_line)))
    return json.dumps({'status': 'ok', 'filepath': filepath, 'content': 'import warnings\nx = 1\n', 'start_line': 1, 'end_line': 2, 'total_lines': 2, 'is_truncated': False})
def run_command(command: str) -> str:
    """Execute a shell command inside the repository sandbox.

    Args:
        command: Shell command to execute.
    """
    seen.append(('run_command', command[:80]))
    return json.dumps({'status': 'ok', 'stdout': '303:class Header(Param):\n', 'stderr': '', 'exit_code': 0})
def submit_patch() -> str:
    """Capture the current working tree modifications as the agent's submission."""
    seen.append(('submit_patch',))
    return json.dumps({'status': 'ok', 'patch_size': 10, 'files_changed': 1})
raw = []
class Cap(litellm.integrations.custom_logger.CustomLogger):
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            m = response_obj.choices[0].message
            raw.append({'tool_calls': [(t.function.name, t.function.arguments) for t in (m.tool_calls or [])], 'content': (m.content or '')[:120], 'reasoning': (getattr(m, 'reasoning_content', None) or '')[:80], 'finish': response_obj.choices[0].finish_reason})
        except Exception as e:
            raw.append({'err': str(e)})
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self.log_success_event(kwargs, response_obj, start_time, end_time)
litellm.callbacks = [Cap()]
async def run(label, extra):
    seen.clear(); raw.clear()
    model = LiteLlm(model='openai/gemma-4-31b-it-qat-w4a16-ct', api_base='http://127.0.0.1:8001/v1', api_key='EMPTY', num_retries=1, **extra)
    agent = LlmAgent(name='swe_agent', model=model, instruction='You are an autonomous software engineer working in /workspace. Use tools; never describe a tool call in prose.', tools=[run_command, read_file, submit_patch], generate_content_config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=1024))
    ss = InMemorySessionService(); s = await ss.create_session(app_name='p', user_id='u')
    r = Runner(app_name='p', agent=agent, session_service=ss)
    msg = types.Content(role='user', parts=[types.Part(text='Show me lines 300 to 320 of fastapi/params.py with read_file, then grep for "class Header" with run_command, then call submit_patch.')])
    try:
        async for ev in r.run_async(user_id='u', session_id=s.id, new_message=msg):
            pass
    except Exception as e:
        print(label, 'RUN ERROR:', type(e).__name__, str(e)[:300])
    print(f'##### {label}')
    for x in raw: print('  server:', json.dumps(x)[:400])
    print('  tool args received:', seen)
async def main():
    await run('thinking OFF (include_thoughts:false path)', {'extra_body': {'chat_template_kwargs': {'enable_thinking': False}}})
    await run('thinking ON, reasoning_effort=low (day-2/3 style thinking_level)', {'extra_body': {'chat_template_kwargs': {'enable_thinking': True}}, 'reasoning_effort': 'low'})
    await run('thinking ON, no reasoning_effort (organizer sample now)', {'extra_body': {'chat_template_kwargs': {'enable_thinking': True}}})
asyncio.run(main())
