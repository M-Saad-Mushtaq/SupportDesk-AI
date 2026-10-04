# SupportDesk AI: customer support with inspectable AI assistance

[Portfolio overview](../../README.md) | [Architecture](architecture.md) | [Recording guide](demo-script.md)

## Problem and intended users

A small online store's support team needs to answer policy questions, look up
orders, and move difficult conversations to a person without losing context.
Customers need a clear reply and a way to request human help. Staff need to see
what information an assistant used before continuing the conversation.

SupportDesk AI explores that workflow as a **self-directed portfolio project**.
It was not commissioned by a client, and no customer outcomes, time savings,
accuracy gains, or revenue improvements have been measured.

## Implemented solution

The customer chat and staff dashboard share a FastAPI backend. A customer selects
a fictional identity, continues an order conversation, and sends a public message.
The message is saved before the agent runs. The staff Inbox sees the same record;
AI and staff public replies appear in customer chat through visibility-aware
polling. Saved history survives refresh and restart.

The agent can search uploaded policies, read an order belonging to the current
customer, or request a human. Policy replies carry validated source references
and exact quoted excerpts, inspectable in the **staff** Inbox and Agent Activity.
Customer chat shows public reply text, not staff citation cards or tool payloads.
When evidence is missing or a run fails, the interface shows clarification or a
failure/retry state rather than a fabricated successful result.

A human request pauses AI handling. Staff can take over, reply, and add an internal
note. Customer-facing endpoints exclude notes and private activity on the server.
Resuming AI keeps the history and waits for the next new customer message. Resolved
tickets remain inactive until staff explicitly reopen them. Status and handling
mode are separate, persisted fields.

The Knowledge Base accepts text-based PDF, TXT, and Markdown files up to 10 MB.
It stores private files, extracts text, preserves page or section locations,
deduplicates identical uploads, and supports preview, passage search, and confirmed
deletion. Scanned PDFs without extractable text report that OCR is needed.
Overview counts come from stored tickets; settings and actual agent runs persist.

## Technology and architecture

React, TypeScript, and Vite provide the responsive navy/teal UI adapted from Stitch
references. Python/FastAPI serves validated APIs. SQLAlchemy manages SQLite records
and short transactions; Alembic manages explicit schema migrations. Local PDF text
extraction uses pypdf. Idempotency keys protect retried conversation writes.

The agent runner owns orchestration and handling checks. Application-owned model
and tool contracts separate it from the official Google SDK adapter and the offline
mock adapter. The tool registry validates arguments and uses existing retrieval,
order, and handling services. Limits bound requests, tools, context, and retries.
Private model thoughts are not exposed as tool activity.

**Document retrieval uses SQLite FTS5, not embeddings or vector search.** A
parameterized keyword fallback is available if FTS5 is absent. The replaceable
`PassageRetriever` interface leaves room for another retrieval implementation;
that extension is not implemented. Search depends on matching words and is not
semantic understanding. Citation validation checks retrieved IDs and verbatim
quotes, not the truth of every sentence in a model answer.

## What is real and what is fictional

| Area | Implemented behavior | Qualification |
| --- | --- | --- |
| Conversations and handover | SQLite writes, scope checks, notes, status changes, takeover/resume, retry protection | Local workspace only; no email, SMS, or other external delivery |
| Documents and evidence | Actual upload, extraction, FTS5 retrieval, saved source excerpts | Use fictional policy files; no OCR or embeddings |
| Orders | Server-scoped lookup of the selected customer's stored order | Products, customers, shipping updates, and historical seed events are fictional |
| Offline mock mode | Deterministic provider invokes the same real local tools and runner | Model decisions and reply wording are simulated and labeled |
| Gemini mode | Provider adapter and explicit configuration are implemented | Requires the owner's manual configuration; no live call or quality verification was performed for this showcase task |
| Overview and settings | Counts from current records; non-sensitive preferences stored in SQLite | No historical performance analytics; support hours are not a running scheduler |

## Scope and evidence

This is a single-process localhost demo. Customer selection is impersonation of
fictional identities, **not authentication**; staff APIs are unauthenticated too.
Public-response filtering is useful application separation, not production access
control. There is no live carrier integration, external messaging, payment/refund
action, deployment, or production operational guarantee.

The earlier customer-demo milestone reported 70 backend tests, 5 frontend tests,
lint, TypeScript/build, migration checks, and isolated desktop/mobile browser checks.
Those results are preserved in the [development reference](../development.md#customer-demo-verification).
They used fake providers or SDK stubs and do not establish live Gemini answer
quality. This documentation task inspected source and checked links; it did not
rerun those suites, make live calls, or conduct a new visual review.
