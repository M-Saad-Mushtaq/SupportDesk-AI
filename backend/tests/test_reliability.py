"""Retrieval stemming/fallback, index migration, and bounded transient retries.
Isolated SQLite databases, fake models and a stub SDK client only; no network."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from uuid import uuid4
import httpx
import pytest
from alembic import command
from alembic.config import Config
from google.genai import errors, types
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from backend.agent.config import AIConfig
from backend.agent.fake import answer
from backend.agent.gemini import GeminiProvider, classify
from backend.agent.types import ModelRequest, ProviderError, ToolResult
from backend.database import make_engine
from backend.models import ActivityEvent, AgentRun, AgentTool, Message
from backend.retrieval import SQLiteRetriever
from backend.tests.test_agent import agent, begin, current, tool  # noqa: F401  (fixture)
from backend.tests.test_api import mutate
from backend.tests.test_documents import library, upload  # noqa: F401  (fixture)

POLICY = b"""# Fictional Demo Store Policies

## Returns
Unused items may be returned within 30 days with proof of purchase. A support
specialist reviews damaged or faulty items and any replacement or refund request.

## Shipping
Standard shipping in this fictional store takes five business days after dispatch.
Weather can delay delivery.
"""
INCIDENTAL = b"# Gift cards\nGift cards are not items we can refund once used, and they never expire.\n"


def search(engine, query, keyword=False):
    with Session(engine) as session:
        return SQLiteRetriever(force_keyword=keyword).search(session, query, 3)


def run_id(agent, text='How many days do I have to return an unused item?'):
    rid = begin(agent, text)
    asyncio.run(agent[2].execute(rid))
    return rid


def cite(quote):
    return lambda request, results: answer('policy', 'You have 30 days.', [{'source_id': results[0].data['sources'][0]['source_id'], 'quote': quote}])


# --- Task A: retrieval ---

@pytest.mark.parametrize('keyword', [False, True])
def test_stemming_and_partial_fallback_find_the_return_policy(library, keyword):
    client, engine, _, _ = library
    upload(client, 'shipping-returns.md', POLICY, 'text/markdown')
    upload(client, 'gift-cards.md', INCIDENTAL, 'text/markdown')
    for word in ('return', 'returns', 'returned', 'RETURNING'):
        found = search(engine, word, keyword)
        assert found['match'] == 'all_terms' and found['results'], word
        assert found['results'][0]['section'] == 'Returns'
    # The first query from the interrupted recording: "window" exists nowhere.
    found = search(engine, 'return window unused items', keyword)
    assert found['match'] == 'partial_terms'
    assert found['results'][0]['section'] == 'Returns' and '30 days' in found['results'][0]['text']
    # The customer's full question, with stopwords and punctuation.
    found = search(engine, 'How many days do I have to return an unused item?', keyword)
    assert found['results'][0]['section'] == 'Returns'
    assert found['mode'] == ('keyword' if keyword else 'fts5')


def test_ranking_prefers_more_matched_terms_and_unrelated_queries_find_nothing(library):
    client, engine, _, _ = library
    upload(client, 'shipping-returns.md', POLICY, 'text/markdown')
    upload(client, 'gift-cards.md', INCIDENTAL, 'text/markdown')
    # Every word occurs in the policy passage: strict matching returns only it.
    assert [hit['section'] for hit in search(engine, 'refund unused items within days')['results']] == ['Returns']
    # "warranty" occurs nowhere, so partial matching ranks by shared terms:
    # the policy (5 shared) outranks the gift-card text (refund + items).
    found = search(engine, 'refund unused items within days warranty')
    assert found['match'] == 'partial_terms'
    sections = [hit['section'] for hit in found['results']]
    assert sections[0] == 'Returns' and 'Gift cards' in sections
    for query in ('laptop warranty claim procedure', 'quasar nebula'):
        assert search(engine, query)['results'] == []
    # One shared word in a long question is not treated as evidence.
    assert search(engine, 'cancel subscription billing items')['results'] == []


@pytest.mark.parametrize('query', ['', '   ', '"', 'NEAR(', 'return* OR "x', 'a AND b; DROP TABLE documents', '()', ':-'])
def test_fts_syntax_and_empty_queries_are_safe(library, query):
    client, engine, _, _ = library
    upload(client, 'shipping-returns.md', POLICY, 'text/markdown')
    assert isinstance(search(engine, query)['results'], list)
    with Session(engine) as session:
        assert session.scalar(text("SELECT count(*) FROM documents")) == 1
    response = client.get('/api/documents/search', params={'q': query})
    assert response.status_code == 200 and response.json()['match'] in ('all_terms', 'partial_terms', 'none')


def test_index_migration_preserves_chunks_runs_and_citations(tmp_path):
    """Upgrade from the previous head: chunk IDs are unchanged, the active-run
    index survives, stemmed search works on old rows, and triggers still sync."""
    url = f"sqlite:///{tmp_path / 'old.db'}"
    config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
    config.attributes['database_url'] = url
    command.upgrade(config, 'c901bfe20a13')
    engine = make_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO documents (id, title, filename, storage_name, format, size, content_hash, status, created_at, updated_at, page_count, segments) VALUES ('doc-1','returns','returns.md','x.md','MD',10,'h','ready','t','t',0,'[]')")
        connection.exec_driver_sql("INSERT INTO document_chunks (id, document_id, position, page, section, text) VALUES (41, 'doc-1', 1, NULL, 'Returns', 'Unused items may be returned within 30 days.')")
        assert connection.exec_driver_sql("SELECT count(*) FROM document_fts WHERE document_fts MATCH 'return'").scalar() == 0  # unstemmed before
    engine.dispose()
    command.upgrade(config, 'head')
    command.check(config)
    engine = make_engine(url)
    with Session(engine) as session:
        assert session.scalar(text("SELECT id FROM document_chunks")) == 41
        assert 'porter' in session.scalar(text("SELECT sql FROM sqlite_master WHERE name='document_fts'"))
        assert session.scalar(text("SELECT count(*) FROM sqlite_master WHERE type='index' AND name='one_active_agent_run'")) == 1
    found = search(engine, 'return')
    assert [hit['id'] for hit in found['results']] == [41] and found['results'][0]['location'] == 'Section: Returns'
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM document_chunks WHERE id = 41")
    assert search(engine, 'return')['results'] == []
    engine.dispose()
    command.downgrade(config, 'c901bfe20a13')
    command.upgrade(config, 'head')


def test_citations_validate_and_repeated_searches_reuse_results(agent):
    upload(agent[0], 'shipping-returns.md', POLICY, 'text/markdown')
    agent[3].script = [tool('search_knowledge_base', {'query': 'Return  WINDOW unused items'}), tool('search_knowledge_base', {'query': 'return window unused items'}, 'again'), cite('returned within 30 days')]
    result = agent[0].get('/api/agent/runs/' + run_id(agent)).json()
    assert result['status'] == 'completed'
    # Case/spacing variants are one search: the second call reused the first result.
    assert len([t for t in result['tools'] if t['name'] == 'search_knowledge_base']) == 1
    message = current(agent)['messages'][-1]
    assert message['sources'][0]['section'] == 'Section: Returns' and message['sources'][0]['quote'] == 'returned within 30 days'


# --- Task B: transient provider failures ---

def unavailable():
    return ProviderError('provider', 'Gemini is temporarily unavailable. Retry manually later.', None, True, 'HTTP 503 UNAVAILABLE: high demand')


def fast(agent, retries=2):
    agent[2].config = AIConfig(transient_retries=retries)
    waits = []
    async def sleep(seconds):
        waits.append(seconds)
    agent[2].sleep = sleep
    return waits


def test_503_then_success_retries_only_the_failed_model_step(agent):
    upload(agent[0], 'shipping-returns.md', POLICY, 'text/markdown')
    waits = fast(agent)
    agent[3].script = [tool('search_knowledge_base', {'query': 'return'}), unavailable(), cite('returned within 30 days')]
    result = agent[0].get('/api/agent/runs/' + run_id(agent)).json()
    assert result['status'] == 'completed' and result['transient_retries'] == 1 and result['retrying_until'] is None
    assert result['request_count'] == 3 and len(result['tools']) == 1  # search executed once
    sent = agent[3].results
    assert sent[1] == sent[2] and sent[2][0].name == 'search_knowledge_base'  # identical step resent
    assert 1 <= sum(waits) <= 2  # first backoff: 1-2 s with jitter
    assert len([m for m in current(agent)['messages'] if m['text'] == 'You have 30 days.']) == 1


def test_persistent_503_stops_within_limits_and_records_detail(agent):
    fast(agent)
    agent[3].script = [unavailable(), unavailable(), unavailable(), answer('clarification', 'never sent')]
    result = agent[0].get('/api/agent/runs/' + run_id(agent)).json()
    assert result['status'] == 'failed' and result['error_code'] == 'provider'
    assert result['request_count'] == 3 and result['transient_retries'] == 2
    assert result['error_detail'] == 'HTTP 503 UNAVAILABLE: high demand (after 2 automatic retries)'
    assert current(agent)['messages'][-1]['kind'] == 'customer'
    customer = agent[0].get(f"/api/demo/customers/{current(agent)['customer']['id']}/conversations/{agent[4]}").json()
    assert customer['run']['status'] == 'failed' and customer['run']['retrying'] is False and customer['run']['retry_allowed'] is True
    assert 'HTTP 503' not in str(customer)  # staff-only diagnostic


@pytest.mark.parametrize('error', [ProviderError('credentials', 'no', None, False, 'HTTP 401'), ProviderError('configuration', 'no', None, False, 'HTTP 400'), ProviderError('quota', 'exhausted', 60, False, 'HTTP 429'), ProviderError('timeout', 'slow')])
def test_permanent_errors_and_exhausted_quota_never_loop(agent, error):
    waits = fast(agent)
    agent[3].script = [error, answer('clarification', 'never sent')]
    result = agent[0].get('/api/agent/runs/' + run_id(agent)).json()
    assert result['status'] == 'failed' and result['request_count'] == 1 and result['transient_retries'] == 0 and waits == []


def test_retry_delay_longer_than_limit_is_not_waited(agent):
    fast(agent)
    agent[3].script = [ProviderError('rate_limit', 'wait', 45, True, 'HTTP 429'), answer('clarification', 'never sent')]
    result = agent[0].get('/api/agent/runs/' + run_id(agent)).json()
    assert result['status'] == 'failed' and result['request_count'] == 1 and result['retry_at']


def test_no_automatic_retries_when_disabled(agent):
    fast(agent, retries=0)
    agent[3].script = [unavailable(), answer('clarification', 'never sent')]
    assert agent[0].get('/api/agent/runs/' + run_id(agent)).json()['request_count'] == 1


@pytest.mark.parametrize('resume', [False, True])
def test_takeover_during_retry_wait_blocks_the_ai_reply(agent, resume):
    agent[2].config = AIConfig(transient_retries=2)
    waiting, release = Event(), Event()
    async def sleep(seconds):
        waiting.set()
        await asyncio.to_thread(release.wait, 5)
    agent[2].sleep = sleep
    agent[3].script = [unavailable(), answer('clarification', 'AI reply after outage')]
    rid = begin(agent)
    with ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, agent[2].execute(rid))
        assert waiting.wait(5)
        try:
            # The retry wait holds no write transaction: staff actions succeed meanwhile.
            run = agent[0].get('/api/agent/runs/' + rid).json()
            assert run['status'] == 'running' and run['retrying_until']
            customer = agent[0].get(f"/api/demo/customers/{current(agent)['customer']['id']}/conversations/{agent[4]}").json()
            assert customer['run']['retrying'] is True and 'retrying' in customer['run']['message']
            assert mutate(agent[0], '/api/conversations/' + agent[4] + '/takeover').status_code == 200
            if resume:
                assert mutate(agent[0], '/api/conversations/' + agent[4] + '/resume').status_code == 200
        finally:
            release.set()
        future.result(timeout=10)
    result = agent[0].get('/api/agent/runs/' + rid).json()
    assert result['status'] == 'cancelled' and result['retrying_until'] is None and result['request_count'] == 1
    assert not any(m['text'] == 'AI reply after outage' for m in current(agent)['messages'])


def test_handover_after_transient_retry_happens_once(agent):
    fast(agent)
    agent[3].script = [unavailable(), tool('request_human_handover', {'reason': 'Customer asked for a person.'}), answer('clarification', 'never')]
    run_id(agent, 'Please connect me with a person.')
    with Session(agent[1]) as session:
        assert session.scalar(select(func.count()).select_from(AgentTool).where(AgentTool.name == 'request_human_handover')) == 1
        assert session.scalar(select(func.count()).select_from(ActivityEvent).where(ActivityEvent.title == 'Agent requested human support')) == 1
        assert len(session.scalars(select(Message).where(Message.text.contains('requested human support'))).all()) == 1
    assert current(agent)['handling_mode'] == 'awaiting_human'


def test_manual_retry_after_final_failure_and_after_restart(agent):
    upload(agent[0], 'shipping-returns.md', POLICY, 'text/markdown')
    fast(agent)
    agent[3].script = [tool('search_knowledge_base', {'query': 'return'}), unavailable(), unavailable(), unavailable()]
    rid = run_id(agent)
    failed = agent[0].get('/api/agent/runs/' + rid).json()
    assert failed['status'] == 'failed' and failed['tool_count'] == 1
    agent[3].script = [tool('search_knowledge_base', {'query': 'return'}), cite('returned within 30 days')]
    key = str(uuid4())
    assert agent[2].retry(rid, key) == agent[2].retry(rid, key)  # idempotent manual retry
    asyncio.run(agent[2].execute(rid))
    asyncio.run(agent[2].execute(rid))  # duplicate execution is a no-op
    done = agent[0].get('/api/agent/runs/' + rid).json()
    assert done['status'] == 'completed' and done['attempt'] == 2 and done['transient_retries'] == 0
    assert done['attempts'][0]['transient_retries'] == 2 and 'HTTP 503' in done['attempts'][0]['error_detail']
    assert len([m for m in current(agent)['messages'] if m['text'] == 'You have 30 days.']) == 1
    # A restart during a retry wait leaves an interrupted run, recoverable the same way.
    rid2 = begin(agent, 'Second question about returns')
    with Session(agent[1]) as session:
        run = session.get(AgentRun, rid2)
        run.status, run.retrying_until = 'running', '2999-01-01T00:00:00+00:00'
        session.commit()
    agent[2].recover()
    interrupted = agent[0].get('/api/agent/runs/' + rid2).json()
    assert interrupted['status'] == 'interrupted' and interrupted['retrying_until'] is None
    agent[3].script = [tool('search_knowledge_base', {'query': 'return'}), cite('returned within 30 days')]
    agent[2].retry(rid2, str(uuid4()))
    asyncio.run(agent[2].execute(rid2))
    assert agent[0].get('/api/agent/runs/' + rid2).json()['status'] == 'completed'


# --- Gemini adapter: classification and exact-step resend (stub SDK) ---

def api_error(code, status, details=None, headers=None):
    body = {'error': {'code': code, 'status': status, 'message': 'sanitized message', 'details': details or []}}
    return errors.APIError(code, body, httpx.Response(code, headers=headers or {}))


PER_MINUTE = [{'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '7s'}]
PER_DAY = [{'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '7s'}]


@pytest.mark.parametrize('error, code, transient, delay', [
    (api_error(503, 'UNAVAILABLE'), 'provider', True, None),
    (api_error(500, 'INTERNAL'), 'provider', True, None),
    (api_error(503, 'UNAVAILABLE', headers={'retry-after': '3'}), 'provider', True, 3),
    (api_error(429, 'RESOURCE_EXHAUSTED', PER_MINUTE), 'rate_limit', True, 7),
    (api_error(429, 'RESOURCE_EXHAUSTED', PER_DAY), 'quota', False, 7),
    (api_error(429, 'RESOURCE_EXHAUSTED'), 'quota', False, 60),
    (api_error(401, 'UNAUTHENTICATED'), 'credentials', False, None),
    (api_error(400, 'INVALID_ARGUMENT'), 'configuration', False, None),
    (api_error(404, 'NOT_FOUND'), 'configuration', False, None),
    (api_error(501, 'NOT_IMPLEMENTED'), 'provider', False, None),
])
def test_gemini_error_classification(error, code, transient, delay):
    result = classify(error, AIConfig(key='test-only-key').sanitize)
    assert (result.code, result.transient, result.retry_after) == (code, transient, delay)
    assert result.detail.startswith(f'HTTP {error.code} {error.status}')


def test_failed_gemini_step_is_resent_unchanged_with_tool_metadata():
    calls = []
    first = types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role='model', parts=[types.Part(function_call=types.FunctionCall(id='call-1', name='search', args={'query': 'return'}), thought_signature=b'sig')]), finish_reason='STOP')])
    final = types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role='model', parts=[types.Part(text='done')]), finish_reason='STOP')])
    outcomes = [first, api_error(503, 'UNAVAILABLE'), final]
    async def generate(**kwargs):
        calls.append(list(kwargs['contents']))
        item = outcomes.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    config = AIConfig(provider='gemini', model='gemini-3.8-flash', key='test-only-key', free_tier_confirmed=True)
    session = GeminiProvider(config, lambda **_: client).start(ModelRequest('rules', [{'role': 'user', 'text': 'q'}], [{'name': 'search', 'description': 'd', 'parameters': {'type': 'object'}}], 256))
    results = [ToolResult('call-1', 'search', {'sources': []})]
    async def turn():
        await session.complete([], 5)
        with pytest.raises(ProviderError) as failure:
            await session.complete(results, 5)
        assert failure.value.transient
        assert (await session.complete(results, 5)).text == 'done'  # same step, same results
    asyncio.run(turn())
    assert len(calls[1]) == len(calls[2]) == 3
    assert calls[2][1].parts[0].thought_signature == b'sig'  # continuation metadata kept
    assert calls[2][2].parts[0].function_response.id == 'call-1'
    assert len(session.contents) == 4  # q, call, response, final: no duplicated response
