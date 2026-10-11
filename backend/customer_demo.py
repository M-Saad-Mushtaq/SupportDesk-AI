"""Public-only projection for local demo impersonation. This is NOT authentication."""
import json
from pathlib import Path
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.agent.api import CustomerInput, RetryKey
from backend.agent.runner import ACTIVE
from backend.models import AgentRun, Conversation, Customer, Message, Order
from backend.service import add_event, idempotent_write, now

# Only the original fictional identities can be selected, never arbitrary CRM rows.
DEMO_IDS = frozenset('CUS-' + ticket['id'].removeprefix('TKT-') for ticket in json.loads(Path(__file__).with_name('seed_data.json').read_text(encoding='utf-8'))['tickets'])

class Identity(BaseModel):
    id: str
    name: str

class PublicTicket(BaseModel):
    id: str
    subject: str
    order_id: str
    status: Literal['open', 'in_progress', 'resolved']

class CustomerHome(BaseModel):
    customer: Identity
    order_ids: list[str]
    conversations: list[PublicTicket]

class PublicMessage(BaseModel):
    id: str
    kind: Literal['customer', 'ai', 'reply']
    text: str
    created_at: str
    origin: Literal['customer', 'human', 'ai', 'mock', 'sample']

class PublicRun(BaseModel):
    id: str
    status: Literal['pending', 'running', 'completed', 'failed', 'cancelled', 'interrupted']
    retry_allowed: bool
    retrying: bool
    retry_at: str | None
    message: str | None

class PublicConversation(PublicTicket):
    customer: Identity
    handling_mode: Literal['ai', 'human', 'awaiting_human']
    messages: list[PublicMessage]
    run: PublicRun | None

class StartInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    order_id: str = Field(min_length=1, max_length=80)


def identity(session, customer_id):
    customer = session.get(Customer, customer_id) if customer_id in DEMO_IDS else None
    if customer is None:
        raise HTTPException(404, 'Demo customer not found.')
    return customer


def scoped_ticket(session, customer_id, conversation_id):
    identity(session, customer_id)
    ticket = session.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.customer_id == customer_id))
    if ticket is None:
        raise HTTPException(404, 'Demo conversation not found for this customer.')
    return ticket


def summary(ticket):
    return {key: getattr(ticket, key) for key in ('id', 'subject', 'order_id', 'status')}


def public_conversation(session, ticket, runner):
    customer = identity(session, ticket.customer_id)
    # Explicit SQL whitelist: notes are never even loaded by this projection.
    messages = session.scalars(select(Message).where(Message.conversation_id == ticket.id, Message.kind.in_(('customer', 'ai', 'reply'))).order_by(Message.position)).all()
    run = session.scalar(select(AgentRun).where(AgentRun.conversation_id == ticket.id).order_by(AgentRun.created_at.desc(), AgentRun.id.desc()).limit(1))
    public_run = None
    if run:
        last_customer = next((message.id for message in reversed(messages) if message.kind == 'customer'), None)
        active = session.scalar(select(AgentRun.id).where(AgentRun.conversation_id == ticket.id, AgentRun.status.in_(ACTIVE)))
        retry_allowed = (run.status in ('failed', 'interrupted') and run.attempt < runner.config.max_attempts and ticket.status != 'resolved' and ticket.handling_mode == 'ai' and ticket.handling_revision == run.handling_revision and last_customer == run.customer_message_id and not active and (not run.retry_at or now() >= run.retry_at))
        # Never pass raw staff/provider/tool diagnostics through this API.
        labels = {'failed': 'The AI reply could not be completed. Retry when available, or ask the demo staff for help.', 'interrupted': 'The reply was interrupted. It was not retried automatically.', 'cancelled': 'Automatic reply stopped because support handling changed.'}
        # True only during an active automatic backoff wait for a running turn.
        retrying = run.status in ACTIVE and bool(run.retrying_until)
        message = 'AI temporarily unavailable - retrying automatically.' if retrying else labels.get(run.status)
        public_run = {'id': run.id, 'status': run.status, 'retry_allowed': bool(retry_allowed), 'retrying': retrying, 'retry_at': run.retry_at, 'message': message}
    return {**summary(ticket), 'customer': {'id': customer.id, 'name': customer.name}, 'handling_mode': ticket.handling_mode, 'messages': [{'id': message.id, 'kind': message.kind, 'text': message.text, 'created_at': message.created_at, 'origin': 'customer' if message.kind == 'customer' else 'human' if message.kind == 'reply' else 'mock' if message.origin == 'mock' else 'ai' if message.origin == 'gemini' else 'sample'} for message in messages], 'run': public_run}


def customer_router(runner):
    router = APIRouter(prefix='/api/demo', tags=['Customer demo'], responses={404: {'description': 'Unknown fictional customer or conversation/run outside selected customer scope.'}, 409: {'description': 'Resolved conversation, active AI turn, stale retry, or duplicate-key conflict.'}, 429: {'description': 'Retry cooldown has not elapsed.'}})

    @router.get('/customers', response_model=list[Identity])
    def customers():
        """Minimal fictional identity picker only. Demo impersonation is not authentication; no email, order, or message data is listed here."""
        with Session(runner.engine) as session:
            return [{'id': customer.id, 'name': customer.name} for customer in session.scalars(select(Customer).where(Customer.id.in_(DEMO_IDS)).order_by(Customer.name))]

    @router.get('/customers/{customer_id}', response_model=CustomerHome)
    def home(customer_id: str):
        with Session(runner.engine) as session:
            customer = identity(session, customer_id)
            return {'customer': {'id': customer.id, 'name': customer.name}, 'order_ids': list(session.scalars(select(Order.id).where(Order.customer_id == customer_id).order_by(Order.id))), 'conversations': [summary(ticket) for ticket in session.scalars(select(Conversation).where(Conversation.customer_id == customer_id).order_by(Conversation.created_at.desc()))]}

    def read(customer_id, conversation_id):
        with Session(runner.engine) as session:
            return public_conversation(session, scoped_ticket(session, customer_id, conversation_id), runner)

    @router.get('/customers/{customer_id}/conversations/{conversation_id}', response_model=PublicConversation)
    def conversation(customer_id: str, conversation_id: str):
        """Public messages and minimal handling/run status only. No notes, activity, tool payloads, settings, source documents, or other customers' fields."""
        return read(customer_id, conversation_id)

    @router.post('/customers/{customer_id}/conversations', response_model=PublicConversation)
    def start(customer_id: str, body: StartInput, idempotency_key: RetryKey):
        """Start or continue the selected customer's stored order conversation. Existing resolved conversations stay resolved; staff must explicitly reopen them. Does not seed data or trigger generation."""
        def create(session):
            identity(session, customer_id)
            order = session.scalar(select(Order).where(Order.id == body.order_id, Order.customer_id == customer_id))
            if order is None:
                raise HTTPException(404, 'Demo order not found for this customer.')
            ticket = session.scalar(select(Conversation).where(Conversation.customer_id == customer_id, Conversation.order_id == order.id).order_by(Conversation.created_at.desc()).limit(1))
            if ticket is None:
                ticket = Conversation(id='TKT-DEMO-' + uuid4().hex[:12], customer_id=customer_id, order_id=order.id, subject='Demo store support', preview='New customer conversation', channel='Web chat', priority='Normal', status='open', handling_mode='ai', created_at=now(), updated_at=now())
                session.add(ticket)
                session.flush()
                add_event(session, ticket, 'Customer demo conversation started', 'Local fictional customer selection. No authentication or external messaging.')
            return {'conversation_id': ticket.id}
        result = idempotent_write(runner.engine, idempotency_key, 'demo/' + customer_id + '/start', body.model_dump(), create)
        return read(customer_id, result['conversation_id'])

    @router.post('/customers/{customer_id}/conversations/{conversation_id}/messages', response_model=PublicConversation)
    def send(customer_id: str, conversation_id: str, body: CustomerInput, idempotency_key: RetryKey, background_tasks: BackgroundTasks):
        """Uses the existing durable ingestion/agent runner. Idempotent replay responses are projected afresh; the staff snapshot is NEVER returned, including on retries."""
        with Session(runner.engine) as session:
            scoped_ticket(session, customer_id, conversation_id)
        result = runner.accept(conversation_id, body.text, idempotency_key)
        if result['run_id']:
            background_tasks.add_task(runner.execute, result['run_id'])
        return read(customer_id, conversation_id)

    @router.post('/customers/{customer_id}/conversations/{conversation_id}/runs/{run_id}/retry', response_model=PublicConversation)
    def retry(customer_id: str, conversation_id: str, run_id: str, idempotency_key: RetryKey, background_tasks: BackgroundTasks):
        """Explicit retry only for this customer's conversation. Existing backend limits and handling rules remain authoritative."""
        with Session(runner.engine) as session:
            scoped_ticket(session, customer_id, conversation_id)
            run = session.get(AgentRun, run_id)
            if run is None or run.conversation_id != conversation_id:
                raise HTTPException(404, 'Demo run not found for this conversation.')
        runner.retry(run_id, idempotency_key)
        background_tasks.add_task(runner.execute, run_id)
        return read(customer_id, conversation_id)

    return router
