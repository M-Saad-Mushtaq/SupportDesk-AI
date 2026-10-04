# SupportDesk AI - Customer Support Workspace with AI and Human Handover

[Portfolio overview](../../README.md) | [Full case study](case-study.md)

## Short description

I built a local customer-support demo that connects a customer chat to a staff
Inbox. It combines persistent conversations, searchable policy documents,
inspectable agent tool activity, and human takeover/resume. A provider-neutral
runner supports offline mock responses and an optional Gemini adapter. The
responsive React interface uses fictional retail scenarios to demonstrate the
workflow without external customer messaging.

## Five implemented capabilities

1. **Two-sided support chat:** customer messages and staff public replies share
   persistent history, while customer APIs exclude internal notes and private tools.
2. **Human control:** staff can take over, change ticket status, add notes, and
   resume AI; backend rules prevent stale replies and keep resolved tickets inactive.
3. **Local document evidence:** PDF/TXT/Markdown ingestion, previews, SQLite FTS5
   passage search, and saved policy citations visible to staff.
4. **Inspectable agent runs:** validated policy-search, customer-scoped order-lookup,
   and handover tools with recorded inputs/results and explicit failure/retry states.
5. **Persistent staff workspace:** SQLite-backed conversations, current Overview
   counts, support settings, and idempotent writes that survive refresh and restart.

## Technical skills demonstrated

React, TypeScript, responsive UI, Vite API proxying, Python, FastAPI, Pydantic,
SQLAlchemy, SQLite, Alembic migrations, FTS5 retrieval, PDF text extraction,
provider adapters, Google Gen AI SDK integration, tool validation, idempotency,
concurrency guards, visibility-aware polling, and isolated fake-provider testing.
The navy/teal interface was adapted from Stitch design references.

## Project disclosure

This is a **self-directed portfolio project**, not a client engagement or a
production deployment. Customer selection is demo impersonation, not real
authentication. Business data and shipment updates are fictional; there is no
live carrier integration or external message delivery. Retrieval uses FTS5,
not embeddings. No client results, accuracy benchmarks, revenue gains, or time
savings are claimed. Automated verification uses fake providers/SDK stubs;
live Gemini quality was not verified during portfolio preparation.

When presenting a mock recording, include this caption: **"Offline mock mode:
model decisions and reply text are simulated; local tools and persistence are real."**
Do not describe that recording as a live Gemini demonstration.
