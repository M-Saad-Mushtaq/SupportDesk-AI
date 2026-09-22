"""Local test-message and persisted agent-run endpoints."""
from typing import Annotated, Literal
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.models import AgentRun
from backend.agent.runner import run_out

RetryKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")]

class CustomerInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=3000)


def agent_router(runner):
    router = APIRouter(tags=["Agent"], responses={409: {"description": "Resolved ticket, active turn, stale retry, or retry-key conflict. New messages during an AI run are rejected without saving; wait and resubmit."}, 429: {"description": "Explicit retry must wait for the provider retry delay."}, 422: {"description": "Invalid text or missing Idempotency-Key."}})

    @router.get("/api/ai/status")
    def status():
        """Configuration and last successful request in THIS process. Configured does not mean connected. Does not call any provider."""
        return runner.info()

    @router.post("/api/conversations/{conversation_id}/customer-messages")
    def customer_message(conversation_id: str, body: CustomerInput, idempotency_key: RetryKey, background_tasks: BackgroundTasks):
        """Persist a local test customer message BEFORE generation. AI runs only for active AI-handled tickets. Returns pending run_id; poll runs/conversation for completion. Human/awaiting-human stores only the message. Idempotent replays never generate another reply. Resolved requires explicit reopening. Provider errors stay on the run; no mock fallback."""
        result = runner.accept(conversation_id, body.text, idempotency_key)
        if result["run_id"]:
            background_tasks.add_task(runner.execute, result["run_id"])
        return result

    @router.get("/api/agent/runs")
    def runs(conversation_id: str | None = None, status: Literal["pending", "running", "completed", "failed", "cancelled", "interrupted"] | None = None, limit: Annotated[int, Query(ge=1, le=500)] = 200):
        """Actual persisted agent turns, newest first, including safe tool inputs/results and provider-reported usage only. Seeded events are not fabricated runs."""
        with Session(runner.engine) as session:
            query = select(AgentRun)
            if conversation_id:
                query = query.where(AgentRun.conversation_id == conversation_id)
            if status:
                query = query.where(AgentRun.status == status)
            return [run_out(session, run) for run in session.scalars(query.order_by(AgentRun.created_at.desc()).limit(limit))]

    @router.get("/api/agent/runs/{run_id}")
    def run_detail(run_id: str):
        with Session(runner.engine) as session:
            run = session.get(AgentRun, run_id)
            if not run:
                raise HTTPException(404, "Agent run not found.")
            return run_out(session, run)

    @router.post("/api/agent/runs/{run_id}/retry")
    def retry(run_id: str, idempotency_key: RetryKey, background_tasks: BackgroundTasks):
        """Explicit bounded retry of failed/interrupted work. Reuses the incoming message and successful tool actions. May make another provider request; never automatically retries quota errors or interrupted calls. Stale handling/customer context is rejected."""
        result = runner.retry(run_id, idempotency_key)
        background_tasks.add_task(runner.execute, result["run_id"])
        return result

    return router
