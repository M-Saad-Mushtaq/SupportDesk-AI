"""Local SupportDesk API. Run migrations and seed explicitly; never on startup."""
from typing import Annotated
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from backend.database import make_engine
from backend.document_api import document_router
from backend.documents import recover_documents, storage_root
from backend.models import ActivityEvent, Conversation, Customer, SupportSettings
from backend.schemas import ActivityOut, ConversationOut, HandlingMode, MessageInput, OverviewOut, SettingsInput, Status, StatusInput
from backend.service import conversation_out, event_out, get_conversation, idempotent_write, mutate_ticket

RetryKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$", description="Unique key per intended write. Reuse the same key and payload when retrying. Replays return the original response; reusing a key for a different request returns 409.")]
ERRORS = {
    404: {"description": "Record not found; a fresh demo needs explicit seeding."},
    409: {"description": "Handling/status rule conflict, or Idempotency-Key reused with a different request."},
    422: {"description": "Invalid fields, status, handling mode, settings, or missing retry key."},
    503: {"description": "Database unavailable, locked, or migrations have not been applied. Retry after fixing the database."},
}


def create_app(database=None, upload_dir=None, ai_config=None, ai_provider=None):
    engine = database if database is not None else make_engine()

    from backend.agent.runner import AgentRunner
    from backend.agent.api import agent_router
    runner = AgentRunner(engine, ai_config, ai_provider)
    uploads = storage_root(upload_dir)

    @asynccontextmanager
    async def lifespan(_app):
        recover_documents(engine, uploads)
        runner.recover()
        yield
        engine.dispose()

    app = FastAPI(title="SupportDesk AI local demo API", version="0.4.0", lifespan=lifespan, description="SQLite-backed support workspace. No external messages. Explicit mock mode by default; optional privately configured Gemini. Conversation/settings mutation endpoints require Idempotency-Key. Document uploads deduplicate by content hash; document deletion is idempotent. Status (open/in_progress/resolved) is independent of handling mode (ai/human/awaiting_human). Internal notes remain permitted on resolved tickets; public replies, handling transitions, and simulated incoming messages require explicit reopening. No automatic migrations or seeding occur on startup.")
    app.state.engine = engine
    app.state.agent = runner
    app.include_router(agent_router(runner))
    app.include_router(document_router(engine, uploads))

    @app.exception_handler(OperationalError)
    async def database_error(_request, _error):
        return JSONResponse(status_code=503, content={"detail": "Database unavailable. Run Alembic upgrade head, check the database path, and retry. If another process is writing, wait briefly."})

    @app.exception_handler(IntegrityError)
    async def integrity_error(_request, _error):
        return JSONResponse(status_code=409, content={"detail": "Database constraint conflict. Refresh the conversation before trying again."})

    @app.get("/api/health", tags=["Health"])
    def health() -> dict[str, str]:
        """Application liveness; remains available before database setup."""
        return {"status": "ok"}

    @app.get("/api/conversations", response_model=list[ConversationOut], responses=ERRORS, tags=["Conversations"])
    def conversations(q: Annotated[str, Query(max_length=200)] = "", status: Status | None = None, handling_mode: HandlingMode | None = None):
        """Stored conversations, including detail snapshots. Search name, email, ticket/order ID, subject or preview. Filters combine; handling filters exclude resolved tickets."""
        with Session(engine) as session:
            statement = select(Conversation).join(Customer)
            if status:
                statement = statement.where(Conversation.status == status)
            if handling_mode:
                statement = statement.where(Conversation.handling_mode == handling_mode, Conversation.status != "resolved")
            if q.strip():
                statement = statement.where(or_(*[column.icontains(q.strip(), autoescape=True) for column in (Customer.name, Customer.email, Conversation.id, Conversation.order_id, Conversation.subject, Conversation.preview)]))
            return [conversation_out(session, ticket) for ticket in session.scalars(statement.order_by(Conversation.updated_at.desc(), Conversation.id)).all()]

    @app.get("/api/conversations/{conversation_id}", response_model=ConversationOut, responses=ERRORS, tags=["Conversations"])
    def conversation(conversation_id: str):
        """Read a conversation, ordered messages/events, customer, and order from SQLite."""
        with Session(engine) as session:
            return conversation_out(session, get_conversation(session, conversation_id))

    def write(conversation_id, operation, payload, key):
        return idempotent_write(engine, key, f"{conversation_id}/{operation}", payload, lambda session: mutate_ticket(session, get_conversation(session, conversation_id), operation, payload))

    @app.post("/api/conversations/{conversation_id}/messages", response_model=ConversationOut, responses=ERRORS, tags=["Conversations"])
    def message(conversation_id: str, body: MessageInput, idempotency_key: RetryKey):
        """Store a public reply (human handling, active ticket required) or internal note (also allowed when resolved). Never sends externally. Whitespace-only content is rejected."""
        return write(conversation_id, "messages", body.model_dump(), idempotency_key)

    @app.patch("/api/conversations/{conversation_id}/status", response_model=ConversationOut, responses=ERRORS, tags=["Conversations"])
    def status_change(conversation_id: str, body: StatusInput, idempotency_key: RetryKey):
        """Explicitly change/reopen status. Does not alter handling mode or generate a message. Repeating the current status is a no-op."""
        return write(conversation_id, "status", body.model_dump(), idempotency_key)

    @app.post("/api/conversations/{conversation_id}/takeover", response_model=ConversationOut, responses=ERRORS, tags=["Handling"])
    def takeover(conversation_id: str, idempotency_key: RetryKey):
        """Switch an active conversation to human handling and pause AI. Already human is a no-op. Resolved returns 409."""
        return write(conversation_id, "takeover", {}, idempotency_key)

    @app.post("/api/conversations/{conversation_id}/resume", response_model=ConversationOut, responses=ERRORS, tags=["Handling"])
    def resume(conversation_id: str, idempotency_key: RetryKey):
        """Human → AI, preserving history and waiting for the NEXT customer message. No immediate reply. Already AI is a no-op; awaiting_human or resolved returns 409."""
        return write(conversation_id, "resume", {}, idempotency_key)

    @app.post("/api/conversations/{conversation_id}/simulate-customer", response_model=ConversationOut, responses=ERRORS, tags=["Simulation"])
    def simulate(conversation_id: str, idempotency_key: RetryKey):
        """Store a fixed sample customer message. AI handling adds one fixed acknowledgment. Human/awaiting_human modes add no AI response. Resolved returns 409. No external services."""
        return write(conversation_id, "simulate-customer", {}, idempotency_key)

    @app.get("/api/conversations/{conversation_id}/activity", response_model=list[ActivityOut], responses=ERRORS, tags=["Activity"])
    def activity(conversation_id: str):
        with Session(engine) as session:
            get_conversation(session, conversation_id)
            return [event_out(event) for event in session.scalars(select(ActivityEvent).where(ActivityEvent.conversation_id == conversation_id).order_by(ActivityEvent.position))]

    @app.get("/api/activity", response_model=list[ActivityOut], responses=ERRORS, tags=["Activity"])
    def all_activity():
        """Recorded events across conversations. Imported tool outputs and generated acknowledgments remain labeled simulations."""
        with Session(engine) as session:
            return [event_out(event) for event in session.scalars(select(ActivityEvent).order_by(ActivityEvent.created_at, ActivityEvent.conversation_id, ActivityEvent.position))]

    @app.get("/api/settings", response_model=SettingsInput, responses=ERRORS, tags=["Settings"])
    def settings():
        with Session(engine) as session:
            item = session.get(SupportSettings, 1)
            if not item:
                raise HTTPException(404, "Support settings are not initialized. Run the seed command or save settings with PUT /api/settings.")
            return item.data

    @app.put("/api/settings", response_model=SettingsInput, responses=ERRORS, tags=["Settings"])
    def save_settings(body: SettingsInput, idempotency_key: RetryKey):
        """Store only validated non-sensitive preferences. Rejects unknown fields. Same-day hours only. Preferences do not schedule messages or enable real AI automation."""
        payload = body.model_dump()
        def save(session):
            item = session.get(SupportSettings, 1)
            if item:
                item.data = payload
            else:
                session.add(SupportSettings(id=1, data=payload))
            return payload
        return idempotent_write(engine, idempotency_key, "settings", payload, save)

    @app.get("/api/overview", response_model=OverviewOut, responses=ERRORS, tags=["Overview"])
    def overview():
        """Current counts from SQLite. No historical trend, latency, or AI-performance analytics are inferred from the four seed records."""
        with Session(engine) as session:
            count = lambda *conditions: session.scalar(select(func.count()).select_from(Conversation).where(*conditions))
            return {"total": count(), "active": count(Conversation.status != "resolved"), "ai": count(Conversation.status != "resolved", Conversation.handling_mode == "ai"), "awaiting_human": count(Conversation.status != "resolved", Conversation.handling_mode == "awaiting_human"), "resolved": count(Conversation.status == "resolved"), "handover_ids": list(session.scalars(select(Conversation.id).where(Conversation.status != "resolved", Conversation.handling_mode == "awaiting_human").order_by(Conversation.id))), "historical_volume_available": False}

    return app


app = create_app()
