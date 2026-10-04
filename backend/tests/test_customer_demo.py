"""Public API privacy and complete two-sided workflow; no live providers."""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.agent.config import AIConfig
from backend.agent.fake import answer
from backend.agent.types import ProviderError
from backend.database import make_engine, write_session
from backend.main import create_app
from backend.models import AgentRun, AgentTool, Customer, Order, Message, SupportSettings
from backend.tests.test_agent import agent
from backend.tests.test_api import mutate
from backend.tests.test_documents import upload


def paths(agent):
    staff = '/api/conversations/' + agent[4]
    customer = agent[0].get(staff).json()['customer']['id']
    return '/api/demo/customers/' + customer, staff, customer


def view(agent):
    base, _, _ = paths(agent)
    return base + '/conversations/' + agent[4]


def send(agent, text, key=None):
    return mutate(agent[0], view(agent) + '/messages', {'text': text}, key)


def assert_public(value):
    assert set(value) == {'id', 'subject', 'order_id', 'status', 'customer', 'handling_mode', 'messages', 'run'}
    assert set(value['customer']) == {'id', 'name'}
    for message in value['messages']:
        assert set(message) == {'id', 'kind', 'text', 'created_at', 'origin'}
        assert message['kind'] in ('customer', 'ai', 'reply')
    if value['run']:
        assert set(value['run']) == {'id', 'status', 'retry_allowed', 'retry_at', 'message'}


def test_public_whitelist_includes_no_private_fields_even_on_replayed_writes(agent):
    client, engine, runner, provider, ticket, _, _ = agent
    base, staff, customer = paths(agent)
    mutate(client, staff + '/messages', {'kind': 'note', 'text': 'PRIVATE-NOTE-MARKER'})
    with write_session(engine) as session:
        settings = session.get(SupportSettings, 1)
        settings.data = {**settings.data, 'company': 'PRIVATE-SETTINGS-MARKER'}
        session.add(Customer(id='REAL-ROW', name='NOT-A-DEMO-CUSTOMER', email='private@example.com', profile={}))
        session.commit()
    key = str(uuid4())
    provider.script = [ProviderError('provider', 'PRIVATE-PROVIDER-DIAGNOSTIC')]
    first = send(agent, 'Public question', key)
    assert first.status_code == 200
    assert_public(first.json())
    with Session(engine) as session:
        run = session.scalar(select(AgentRun).where(AgentRun.conversation_id == ticket))
        assert run.error == 'PRIVATE-PROVIDER-DIAGNOSTIC'
    read = client.get(view(agent))
    replay = send(agent, 'Public question', key)
    for response in (read, replay, client.get(base), client.get('/api/demo/customers')):
        for private in ('PRIVATE-NOTE-MARKER', 'PRIVATE-SETTINGS-MARKER', 'PRIVATE-PROVIDER-DIAGNOSTIC', 'NOT-A-DEMO-CUSTOMER', 'private@example.com'):
            assert private not in response.text
    assert_public(replay.json())
    assert client.get('/api/demo/customers/REAL-ROW').status_code == 404
    assert all(set(item) == {'id', 'name'} for item in client.get('/api/demo/customers').json())
    # Even an original staff ingestion retry key cannot leak its stored full snapshot.
    staff_key = str(uuid4())
    runner.accept(ticket, 'From staff test control', staff_key)
    replay = send(agent, 'From staff test control', staff_key)
    assert_public(replay.json())
    assert 'PRIVATE-NOTE-MARKER' not in replay.text


def test_conversation_and_order_and_run_scope_are_checked_server_side(agent):
    client = agent[0]
    base, staff, customer = paths(agent)
    other = next(item for item in client.get('/api/conversations').json() if item['id'] != agent[4])
    other_path = base + '/conversations/' + other['id']
    assert client.get(other_path).status_code == 404
    assert mutate(client, other_path + '/messages', {'text': 'No access'}).status_code == 404
    assert mutate(client, base + '/conversations', {'order_id': other['order']['id']}).status_code == 404
    send(agent, 'A policy question')
    own_run = client.get(view(agent)).json()['run']['id']
    other_base = '/api/demo/customers/' + other['customer']['id'] + '/conversations/' + other['id']
    assert mutate(client, other_base + '/runs/' + own_run + '/retry').status_code == 404
    assert mutate(client, view(agent) + '/messages', {'text': 'x', 'kind': 'note'}).status_code == 422
    assert mutate(client, view(agent) + '/messages', {'text': '   '}).status_code == 422
    assert client.post(view(agent) + '/messages', json={'text': 'Missing key'}).status_code == 422
    assert client.get(view(agent) + '/activity').status_code == 404
    assert client.get(base + '/settings').status_code == 404


def test_complete_customer_ai_human_handover_resume_sequence(agent):
    client, _, _, provider, ticket, _, _ = agent
    base, staff, _ = paths(agent)
    upload(client, 'demo-returns.md', b'# Returns\nReturns are accepted within 30 days with proof of purchase.')
    assert send(agent, 'What is your returns policy?').status_code == 200
    result = client.get(view(agent)).json()
    assert result['messages'][-1]['kind'] == 'ai'
    assert '30 days' in result['messages'][-1]['text']
    assert result['run']['status'] == 'completed'
    assert any(call for batch in provider.results for call in batch if call.name == 'search_knowledge_base')
    assert send(agent, 'Please connect me with a person.').status_code == 200
    handover = client.get(view(agent)).json()
    assert handover['handling_mode'] == 'awaiting_human'
    assert 'requested human support' in handover['messages'][-1]['text']
    assert mutate(client, staff + '/takeover').status_code == 200
    assert mutate(client, staff + '/messages', {'kind': 'reply', 'text': 'A specialist is here to help.'}).status_code == 200
    assert client.get(view(agent)).json()['messages'][-1]['origin'] == 'human'
    assert client.get(view(agent)).json()['messages'][-1]['text'] == 'A specialist is here to help.'
    mutate(client, staff + '/messages', {'kind': 'note', 'text': 'INTERNAL CUSTOMER MUST NEVER RECEIVE'})
    assert 'INTERNAL CUSTOMER MUST NEVER RECEIVE' not in client.get(view(agent)).text
    before = client.get(view(agent)).json()['messages']
    calls = len(provider.requests)
    mutate(client, staff + '/resume')
    assert client.get(view(agent)).json()['messages'] == before
    assert len(provider.requests) == calls
    assert send(agent, 'Thanks. What is the returns policy?').status_code == 200
    assert len(provider.requests) == calls + 1
    assert 'INTERNAL CUSTOMER MUST NEVER RECEIVE' not in str(provider.requests[-1].history)
    assert 'A specialist is here to help.' in str(provider.requests[-1].history)


def test_human_and_resolved_state_and_continuing_never_reopens(agent):
    client = agent[0]
    base, staff, _ = paths(agent)
    mutate(client, staff + '/takeover')
    before = len(agent[3].requests)
    send(agent, 'Hello to staff')
    assert len(agent[3].requests) == before
    assert client.get(view(agent)).json()['messages'][-1]['kind'] == 'customer'
    mutate(client, staff + '/status', {'status': 'resolved'}, method='patch')
    closed = client.get(view(agent)).json()
    assert send(agent, 'Not reopened').status_code == 409
    continued = mutate(client, base + '/conversations', {'order_id': closed['order_id']}).json()
    assert continued['id'] == agent[4] and continued['status'] == 'resolved'
    assert continued['messages'] == closed['messages']
    mutate(client, staff + '/status', {'status': 'open'}, method='patch')
    assert send(agent, 'After explicit reopening').status_code == 200


def test_duplicate_sends_parallel_requests_and_restart_persistence(agent):
    client, _, _, _, _, url, folder = agent
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: send(agent, 'One public question', key), range(2)))
    assert all(response.status_code == 200 for response in responses)
    result = client.get(view(agent)).json()
    assert len([message for message in result['messages'] if message['text'] == 'One public question']) == 1
    assert len([run for run in client.get('/api/agent/runs').json() if run['conversation_id'] == agent[4]]) == 1
    with TestClient(create_app(make_engine(url), folder, AIConfig())) as restarted:
        assert restarted.get(view(agent)).json() == result
        assert mutate(restarted, view(agent) + '/messages', {'text': 'One public question'}, key).status_code == 200
        assert restarted.get(view(agent)).json() == result


def test_start_missing_conversation_without_duplicate_records_or_auto_generation(agent):
    client, engine, _, provider, _, _, _ = agent
    base, _, customer = paths(agent)
    with write_session(engine) as session:
        original = session.scalar(select(Order).where(Order.customer_id == customer))
        session.add(Order(id='ORD-DEMO-NEW', customer_id=customer, details=original.details))
        session.commit()
    key = str(uuid4())
    first = mutate(client, base + '/conversations', {'order_id': 'ORD-DEMO-NEW'}, key)
    assert first.status_code == 200
    result = first.json()
    assert result['messages'] == [] and result['handling_mode'] == 'ai'
    assert result['run'] is None and provider.requests == []
    assert mutate(client, base + '/conversations', {'order_id': 'ORD-DEMO-NEW'}, key).json()['id'] == result['id']
    assert mutate(client, base + '/conversations', {'order_id': 'ORD-DEMO-NEW'}).json()['id'] == result['id']
    assert result['id'] in [item['id'] for item in client.get('/api/conversations').json()]


def test_public_failure_retry_and_private_tool_results(agent):
    client, engine, _, provider, ticket, _, _ = agent
    provider.script = [ProviderError('quota', 'Staff-only quota diagnostic', 0)]
    send(agent, 'Test failure')
    result = client.get(view(agent)).json()
    assert result['run']['status'] == 'failed' and result['run']['retry_allowed']
    assert 'Staff-only quota diagnostic' not in json.dumps(result)
    provider.script = [answer('clarification', 'Which policy can I help with?')]
    key = str(uuid4())
    path = view(agent) + '/runs/' + result['run']['id'] + '/retry'
    assert mutate(client, path, key=key).status_code == 200
    assert mutate(client, path, key=key).status_code == 200
    result = client.get(view(agent)).json()
    assert result['messages'][-1]['text'] == 'Which policy can I help with?'
    assert result['run']['status'] == 'completed' and not result['run']['retry_allowed']
    # A stored diagnostic payload is not in any public projection.
    with write_session(engine) as session:
        session.add(AgentTool(id=str(uuid4()), run_id=result['run']['id'], fingerprint='private', name='diagnostic', arguments={'secret': 'PRIVATE-TOOL-INPUT'}, result={'secret': 'PRIVATE-TOOL-OUTPUT'}, created_at='2026-01-01', attempt=1))
        session.commit()
    assert 'PRIVATE-TOOL' not in client.get(view(agent)).text
    assert 'PRIVATE-TOOL' not in mutate(client, path, key=key).text
