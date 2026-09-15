from datetime import datetime, timezone
import hashlib
import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select

from backend.database import write_session
from backend.models import ActivityEvent, Conversation, Customer, Message, Order, RequestRecord


def now():
    return datetime.now(timezone.utc).isoformat()


def get_conversation(session, conversation_id):
    ticket = session.get(Conversation, conversation_id)
    if ticket is None:
        raise HTTPException(404, "Conversation not found. For a fresh demo, run the explicit seed command.")
    return ticket


def event_out(event):
    return {key: getattr(event, key) for key in ("id", "conversation_id", "title", "created_at", "input", "result")}


def conversation_out(session, ticket):
    customer = session.get(Customer, ticket.customer_id)
    order = session.get(Order, ticket.order_id)
    messages = session.scalars(select(Message).where(Message.conversation_id == ticket.id).order_by(Message.position)).all()
    events = session.scalars(select(ActivityEvent).where(ActivityEvent.conversation_id == ticket.id).order_by(ActivityEvent.position)).all()
    return {
        **{key: getattr(ticket, key) for key in ("id", "subject", "preview", "channel", "priority", "status", "handling_mode", "created_at", "updated_at")},
        "customer": {**customer.profile, "id": customer.id, "name": customer.name, "email": customer.email},
        "order": {**order.details, "id": order.id},
        "messages": [{key: getattr(message, key) for key in ("id", "kind", "text", "created_at", "sources")} for message in messages],
        "activity": [event_out(event) for event in events],
    }


def position(session, model, conversation_id):
    return (session.scalar(select(func.max(model.position)).where(model.conversation_id == conversation_id)) or 0) + 1


def add_event(session, ticket, title, result, input=None):
    session.add(ActivityEvent(id=str(uuid4()), conversation_id=ticket.id, position=position(session, ActivityEvent, ticket.id), title=title, result=result, input=input, created_at=now()))


def add_message(session, ticket, kind, text):
    session.add(Message(id=str(uuid4()), conversation_id=ticket.id, position=position(session, Message, ticket.id), kind=kind, text=text, created_at=now(), sources=[]))
    if kind != "note":
        ticket.preview = text
    ticket.updated_at = now()


def require_active(ticket):
    if ticket.status == "resolved":
        raise HTTPException(409, "Conversation is resolved. Explicitly reopen it before replying, changing handling, or simulating a customer message.")


def mutate_ticket(session, ticket, operation, payload):
    if operation == "messages":
        if payload["kind"] == "reply":
            require_active(ticket)
            if ticket.handling_mode != "human":
                raise HTTPException(409, "Take over from AI before adding a public reply.")
        add_message(session, ticket, payload["kind"], payload["text"])
        add_event(session, ticket, "Internal note added" if payload["kind"] == "note" else "Demo reply added", "Saved to SQLite. Nothing was sent externally.")
    elif operation == "status":
        if ticket.status != payload["status"]:
            previous = ticket.status
            ticket.status = payload["status"]
            ticket.updated_at = now()
            add_event(session, ticket, "Status changed", f"Status changed from {previous} to {ticket.status}. No automatic reply was generated.")
    elif operation in ("takeover", "resume"):
        require_active(ticket)
        if operation == "takeover" and ticket.handling_mode != "human":
            ticket.handling_mode = "human"
            ticket.updated_at = now()
            add_event(session, ticket, "You took over", "Human handling is active. Automatic AI replies are paused.")
        elif operation == "resume" and ticket.handling_mode != "ai":
            if ticket.handling_mode != "human":
                raise HTTPException(409, "Only a human-controlled conversation can resume AI. Take over first.")
            ticket.handling_mode = "ai"
            ticket.updated_at = now()
            add_event(session, ticket, "AI resumed", "AI handling resumed. Waiting for the next customer message; no reply was generated. Messages and notes are preserved.")
    elif operation == "simulate-customer":
        require_active(ticket)
        add_message(session, ticket, "customer", "Hi, could you give me an update on my request?")
        if ticket.handling_mode == "ai":
            customer = session.get(Customer, ticket.customer_id)
            add_message(session, ticket, "ai", f"Thanks for checking in, {customer.name.split()[0]}. Your request is still recorded. This is a simulated acknowledgment; no order changes have been made.")
        add_event(session, ticket, "Simulated customer message", "A sample customer message was stored. " + ("One fixed AI acknowledgment was added; no AI service was called." if ticket.handling_mode == "ai" else "Automatic AI replies remain paused."))
    session.flush()
    return conversation_out(session, ticket)


def idempotent_write(engine, key, scope, payload, operation):
    fingerprint = hashlib.sha256(json.dumps([scope, payload], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    # BEGIN IMMEDIATE serializes concurrent writers before looking up the key
    # or enforcing a state transition. The response and writes commit together.
    with write_session(engine) as session:
        record = session.get(RequestRecord, key)
        if record:
            if record.fingerprint != fingerprint:
                raise HTTPException(409, "Idempotency-Key was already used for a different request. Use a new key for a new action.")
            return record.response
        response = operation(session)
        session.add(RequestRecord(key=key, fingerprint=fingerprint, response=response))
        session.commit()
        return response
