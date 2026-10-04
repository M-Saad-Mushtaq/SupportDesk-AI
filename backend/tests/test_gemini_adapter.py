"""SDK conversion tests with a stub transport. No requests reach Google."""
import asyncio
from types import SimpleNamespace
import httpx
import pytest
from google.genai import types, errors
from backend.agent.config import AIConfig
from backend.agent.gemini import GeminiProvider, retry_delay
from backend.agent.types import ModelRequest, ProviderError, ToolResult


def response(parts, finish='STOP', usage=None):
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role='model', parts=parts), finish_reason=finish)], usage_metadata=usage)


class StubClient:
    def __init__(self, results):
        self.results, self.calls, self.closed = list(results), [], False
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=self.generate), aclose=self.aclose)

    async def generate(self, **kwargs):
        self.calls.append({**kwargs, 'contents': list(kwargs['contents'])})
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def aclose(self):
        self.closed = True

    def close(self):
        self.closed = True


def setup(results):
    client = StubClient(results)
    options = []
    def factory(**kwargs):
        options.append(kwargs)
        return client
    config = AIConfig(provider='gemini', model='gemini-2.5-flash', key='test-only-key', free_tier_confirmed=True)
    adapter = GeminiProvider(config, factory)
    request = ModelRequest('Application rules', [{'role': 'user', 'text': 'Question'}, {'role': 'assistant', 'text': 'Public human reply'}, {'role': 'user', 'text': 'Follow up'}], [{'name': 'search', 'description': 'Find passages', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string'}}}}], 1024)
    return adapter.start(request), client, options


def test_sdk_continuations_keep_signatures_but_never_expose_thoughts():
    first = response([types.Part(text='PRIVATE REASONING', thought=True), types.Part(function_call=types.FunctionCall(id='provider-call', name='search', args={'query': 'returns'}), thought_signature=b'opaque-signature')], usage=types.GenerateContentResponseUsageMetadata(prompt_token_count=22, candidates_token_count=8, total_token_count=30))
    session, client, options = setup([first, response([types.Part(text='final')])])
    async def turn():
        normalized = await session.complete([], 10)
        assert normalized.text == '' and normalized.finish_reason == 'tool_calls'
        assert normalized.usage == {'input_tokens': 22, 'output_tokens': 8, 'total_tokens': 30}
        assert 'PRIVATE REASONING' not in repr(normalized) and 'opaque-signature' not in repr(normalized)
        assert normalized.calls[0].id == 'provider-call'
        final = await session.complete([ToolResult('provider-call', 'search', {'sources': []})], 8)
        assert final.text == 'final'
        second = client.calls[1]['contents']
        assert second[-2] is first.candidates[0].content
        assert second[-2].parts[-1].thought_signature == b'opaque-signature'
        assert second[-1].parts[0].function_response.id == 'provider-call'
        assert second[-1].parts[0].function_response.name == 'search'
        await session.close()
    asyncio.run(turn())
    assert client.closed and options[0]['vertexai'] is False
    assert options[0]['http_options'].retry_options.attempts == 1
    assert client.calls[0]['config'].automatic_function_calling.disable is True
    assert client.calls[0]['config'].http_options.retry_options.attempts == 1
    assert [c.role for c in client.calls[0]['contents']] == ['user', 'model', 'user']


def test_synthetic_call_ids_and_tool_pair_validation():
    session, _, _ = setup([response([types.Part(function_call=types.FunctionCall(name='search', args={'query': 'x'}))])])
    async def turn():
        result = await session.complete([], 10)
        assert result.calls[0].id
        with pytest.raises(ProviderError, match='did not match'):
            await session.complete([ToolResult(result.calls[0].id, 'wrong_name', {})], 10)
    asyncio.run(turn())


@pytest.mark.parametrize('code, expected', [(429, 'quota'), (401, 'credentials'), (403, 'credentials'), (404, 'configuration'), (400, 'configuration'), (503, 'provider')])
def test_provider_errors_are_safe_and_not_retried(code, expected):
    raw = errors.APIError(code, {'error': {'message': 'SECRET private provider payload'}}, httpx.Response(code, headers={'retry-after': '17'}))
    session, client, _ = setup([raw])
    with pytest.raises(ProviderError) as result:
        asyncio.run(session.complete([], 10))
    assert result.value.code == expected and 'SECRET' not in str(result.value)
    assert len(client.calls) == 1
    if code == 429:
        assert result.value.retry_after == 17


def test_rejected_request_logs_sanitized_status_server_side(caplog):
    payload = {'error': {'code': 404, 'status': 'NOT_FOUND', 'message': 'models/gemini-2.5-flash is not found for key=test-only-key AIzaSyA0123456789abcdefghijklmno see https://example.invalid/v1?key=test-only-key'}}
    session, _, _ = setup([errors.APIError(404, payload, httpx.Response(404))])
    with caplog.at_level('WARNING', logger='backend.agent.gemini'), pytest.raises(ProviderError) as result:
        asyncio.run(session.complete([], 10))
    assert result.value.code == 'configuration' and 'NOT_FOUND' not in str(result.value)
    logged = caplog.text
    assert 'http_status=404' in logged and 'provider_status=NOT_FOUND' in logged and 'model=gemini-2.5-flash' in logged
    assert 'is not found' in logged
    for secret in ('test-only-key', 'AIzaSy', 'https://', 'Follow up', 'Application rules'):
        assert secret not in logged


@pytest.mark.parametrize('failure, code', [(httpx.ReadTimeout('private details'), 'timeout'), (RuntimeError('secret'), 'connection')])
def test_transport_error_mapping(failure, code):
    session, _, _ = setup([failure])
    with pytest.raises(ProviderError) as result:
        asyncio.run(session.complete([], 10))
    assert result.value.code == code and 'private' not in str(result.value) and 'secret' not in str(result.value)


def test_truncated_tool_call_is_not_executed_and_retry_delay_is_bounded():
    session, _, _ = setup([response([types.Part(function_call=types.FunctionCall(name='search', args={'query': 'x'}))], 'MAX_TOKENS')])
    assert asyncio.run(session.complete([], 10)).finish_reason == 'length'
    assert retry_delay(SimpleNamespace(code=429, response=None, details=[{'retryDelay': '12s'}])) == 12
    assert retry_delay(SimpleNamespace(code=429, response=None, details=[])) == 60


def test_default_gemini_model_is_available_to_new_projects(monkeypatch):
    # gemini-2.5-flash returned 404 NOT_FOUND ("no longer available to new users").
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.delenv('AI_MODEL', raising=False)
    assert AIConfig.from_env().model == 'gemini-3.8-flash'
    monkeypatch.setenv('AI_MODEL', 'gemini-2.5-flash')
    assert AIConfig.from_env().model == 'gemini-2.5-flash'  # explicit choice is still honoured


def test_configuration_does_not_fallback_or_expose_keys(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'unsupported')
    monkeypatch.setenv('GEMINI_API_KEY', 'secret-for-test')
    config = AIConfig.from_env()
    assert config.provider == 'invalid' and config.problem()
    assert 'secret-for-test' not in repr(config)
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('AI_MAX_REQUESTS', '999')
    assert 'AI_MAX_REQUESTS' in AIConfig.from_env().problem()
