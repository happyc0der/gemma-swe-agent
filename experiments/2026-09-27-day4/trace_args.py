import asyncio, json, os
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
import litellm
from litellm import ModelResponse
from google.adk.models import lite_llm as L
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import google.adk
seen = []
def read_file(filepath: str, start_line: int | None = None, end_line: int | None = None) -> str:
    """Read a file.

    Args:
        filepath: path.
        start_line: first line.
        end_line: last line.
    """
    seen.append((type(start_line).__name__, start_line))
    return json.dumps({'status': 'ok'})
raw = {"id": "x", "object": "chat.completion", "created": 0, "model": "gemma-4-31b-it-qat-w4a16-ct",
       "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {"role": "assistant", "content": "",
       "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": "{\"end_line\": 320, \"filepath\": \"fastapi/params.py\", \"start_line\": 300}"}}]}}],
       "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
calls = {'n': 0}
async def fake_acompletion(*a, **kw):
    calls['n'] += 1
    if calls['n'] == 1:
        return ModelResponse(**raw)
    return ModelResponse(**{**raw, "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "done"}}]})
async def main():
    model = LiteLlm(model='openai/gemma-4-31b-it-qat-w4a16-ct', api_base='http://x/v1', api_key='EMPTY')
    model.llm_client.acompletion = fake_acompletion
    agent = LlmAgent(name='a', model=model, instruction='x', tools=[read_file])
    ss = InMemorySessionService(); s = await ss.create_session(app_name='p', user_id='u')
    r = Runner(app_name='p', agent=agent, session_service=ss)
    async for ev in r.run_async(user_id='u', session_id=s.id, new_message=types.Content(role='user', parts=[types.Part(text='go')])):
        for p in (ev.content.parts if ev.content else []) or []:
            if p.function_call: print('  event function_call.args:', {k: (type(v).__name__, v) for k, v in p.function_call.args.items()})
    print('ADK', google.adk.__version__, '-> function received:', seen)
asyncio.run(main())
