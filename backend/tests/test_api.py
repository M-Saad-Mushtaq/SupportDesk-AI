from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import make_engine
from backend.main import create_app
from backend.models import ActivityEvent, Conversation, Message, RequestRecord
from backend.seed import seed

ROOT = Path(__file__).resolve().parents[1]


def migrate(url):
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    command.check(config)


@pytest.fixture
def store(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrate(url)
    engine = make_engine(url)
    assert seed(engine) == 4
    with TestClient(create_app(engine)) as client:
        yield client, engine, url


def mutate(client, path, body=None, key=None, method="post"):
    kwargs = {"headers": {"Idempotency-Key": key or str(uuid4())}}
    if body is not None:
        kwargs["json"] = body
    return getattr(client, method)(path, **kwargs)


SARAH = "/api/conversations/TKT-1042"


def test_replies_notes_and_validation(store):
    client, _, _ = store
    before = client.get(SARAH).json()
    assert mutate(client, SARAH + "/messages", {"kind": "reply", "text": "Hello"}).status_code == 409
    note = mutate(client, SARAH + "/messages", {"kind": "note", "text": "  Team only  "}).json()
    assert note["messages"][-1]["kind"] == "note"
    assert note["messages"][-1]["text"] == "Team only"
    assert note["preview"] == before["preview"]
    assert mutate(client, SARAH + "/takeover").status_code == 200
    reply = mutate(client, SARAH + "/messages", {"kind": "reply", "text": "Saved reply"}).json()
    assert reply["messages"][-1]["kind"] == "reply"
    assert reply["preview"] == "Saved reply"
    for payload in ({"kind": "reply", "text": "  "}, {"kind": "customer", "text": "No"}, {"kind": "note", "text": "x" * 5001}, {"kind": "note", "text": "ok", "secret": "no"}):
        assert mutate(client, SARAH + "/messages", payload).status_code == 422
    assert client.post(SARAH + "/takeover").status_code == 422


def test_takeover_resume_waits_and_preserves_history(store):
    client, _, _ = store
    assert mutate(client, SARAH + "/resume").status_code == 409
    waiting = mutate(client, SARAH + "/simulate-customer").json()
    assert waiting["handling_mode"] == "awaiting_human"
    assert waiting["messages"][-1]["kind"] == "customer"
    human = mutate(client, SARAH + "/takeover").json()
    assert human["handling_mode"] == "human"
    paused = mutate(client, SARAH + "/simulate-customer").json()
    assert len(paused["messages"]) == len(human["messages"]) + 1
    assert paused["messages"][-1]["kind"] == "customer"
    resumed = mutate(client, SARAH + "/resume").json()
    assert resumed["handling_mode"] == "ai"
    assert resumed["messages"] == paused["messages"]
    assert resumed["activity"][:-1] == paused["activity"]
    assert resumed["activity"][-1]["title"] == "AI resumed"
    assert mutate(client, SARAH + "/resume").json()["activity"] == resumed["activity"]
    incoming = mutate(client, SARAH + "/simulate-customer").json()
    assert len(incoming["messages"]) == len(resumed["messages"]) + 2
    assert incoming["messages"][-1]["kind"] == "ai"
    assert client.get("/api/conversations/TKT-1035").json()["handling_mode"] == "human"
    assert client.get(SARAH + "/activity").json() == incoming["activity"]


def test_resolved_is_inactive_until_explicit_reopen(store):
    client, _, _ = store
    mutate(client, SARAH + "/takeover")
    closed = mutate(client, SARAH + "/status", {"status": "resolved"}, method="patch").json()
    for operation in ("takeover", "resume", "simulate-customer"):
        assert mutate(client, SARAH + "/" + operation).status_code == 409
    assert mutate(client, SARAH + "/messages", {"kind": "reply", "text": "No"}).status_code == 409
    assert mutate(client, SARAH + "/messages", {"kind": "note", "text": "Allowed internal record"}).status_code == 200
    reopened = mutate(client, SARAH + "/status", {"status": "in_progress"}, method="patch").json()
    assert reopened["status"] == "in_progress"
    assert reopened["handling_mode"] == closed["handling_mode"] == "human"
    assert len(reopened["messages"]) == len(closed["messages"]) + 1
    assert reopened["activity"][-1]["title"] == "Status changed"
    assert mutate(client, SARAH + "/messages", {"kind": "reply", "text": "Now allowed"}).status_code == 200


def test_retries_are_atomic_including_concurrent_requests(store):
    client, engine, _ = store
    key = str(uuid4())
    before = client.get(SARAH).json()
    def post():
        return mutate(client, SARAH + "/messages", {"kind": "note", "text": "Exactly once"}, key)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: post(), range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    current = client.get(SARAH).json()
    assert len(current["messages"]) == len(before["messages"]) + 1
    assert len(current["activity"]) == len(before["activity"]) + 1
    assert mutate(client, SARAH + "/messages", {"kind": "note", "text": "Different"}, key).status_code == 409
    assert mutate(client, SARAH + "/takeover", key=key).status_code == 409
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(RequestRecord)) == 1


def test_duplicate_transitions_do_not_add_events(store):
    client, _, _ = store
    for action, method, body in (("takeover", "post", None), ("resume", "post", None), ("status", "patch", {"status": "resolved"})):
        key = str(uuid4())
        first = mutate(client, SARAH + "/" + action, body, key, method)
        second = mutate(client, SARAH + "/" + action, body, key, method)
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert client.get(SARAH).json() == first.json()


def test_persistence_new_sessions_restart_and_safe_seed(store):
    client, engine, url = store
    key = str(uuid4())
    saved = mutate(client, SARAH + "/messages", {"kind": "note", "text": "Survives restart"}, key).json()
    settings = client.get("/api/settings").json()
    settings["company"] = "Persistent Company"
    assert mutate(client, "/api/settings", settings, method="put").status_code == 200
    mutate(client, SARAH + "/takeover")
    saved = mutate(client, SARAH + "/status", {"status": "resolved"}, method="patch").json()
    assert seed(engine) == 0
    with Session(engine) as session:
        assert session.scalar(select(Message).where(Message.text == "Survives restart")) is not None
        assert session.scalar(select(func.count()).select_from(Conversation)) == 4
    # A separate app and engine are equivalent to reopening the same file after restart.
    with TestClient(create_app(make_engine(url))) as restarted:
        assert restarted.get(SARAH).json() == saved
        assert restarted.get("/api/settings").json()["company"] == "Persistent Company"
        replay = mutate(restarted, SARAH + "/messages", {"kind": "note", "text": "Survives restart"}, key)
        assert replay.status_code == 200
        assert replay.json()["status"] == "open"  # Original acknowledged snapshot.
        assert restarted.get(SARAH).json() == saved  # Replay cannot undo newer changes.


def test_settings_filters_metrics_and_errors(store):
    client, _, _ = store
    stats = client.get("/api/overview").json()
    assert [stats[key] for key in ("total", "active", "ai", "awaiting_human", "resolved")] == [4, 3, 1, 1, 1]
    assert stats["historical_volume_available"] is False
    assert len(client.get("/api/conversations", params={"q": "SARAH", "handling_mode": "awaiting_human"}).json()) == 1
    assert client.get("/api/conversations", params={"q": "ORD-9104"}).json()[0]["customer"]["name"] == "Michael Chang"
    assert client.get("/api/conversations", params={"q": "%"}).json() == []
    assert client.get("/api/conversations", params={"status": "Pending"}).status_code == 422
    assert client.get("/api/conversations/no-such-ticket").status_code == 404
    settings = client.get("/api/settings").json()
    for invalid in ({**settings, "end": "08:00"}, {**settings, "days": []}, {**settings, "api_key": "not allowed"}, {**settings, "escalateDamage": "yes"}):
        assert mutate(client, "/api/settings", invalid, method="put").status_code == 422
    mutate(client, SARAH + "/takeover")
    assert client.get("/api/overview").json()["awaiting_human"] == 0


def test_fresh_migration_is_empty_and_startup_never_seeds(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    migrate(url)
    with TestClient(create_app(make_engine(url))) as client:
        assert client.get("/api/conversations").json() == []
        assert client.get("/api/overview").json()["total"] == 0
        assert client.get("/api/settings").status_code == 404
        assert client.get("/api/health").json() == {"status": "ok"}
    with TestClient(create_app(make_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}"))) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/conversations").status_code == 503
