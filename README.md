# SupportDesk AI

A local customer-support portfolio demo using React, TypeScript, Vite, FastAPI,
SQLAlchemy, Alembic, and SQLite. The existing navy/teal Stitch workspace includes
Inbox, Overview, Knowledge Base, Agent Activity, and Settings. No real AI calls
or messages leave this demo.

## What persists

The default database is `backend/supportdesk.db`. Customers, orders,
conversations, public replies, internal notes, ticket status, handling mode,
activity events, and non-sensitive support settings are stored there. Saved
changes survive browser refresh and backend restart. Overview counts and
handover lists come from the same stored conversations as Inbox; Agent Activity
shows their recorded events. Overview links open the corresponding conversation.

The frontend waits for API acknowledgment before showing success. It provides
loading, empty, saving, and actionable error states. Failed saves retain the
input for retry. After an uncertain network failure, retry the same action so
the existing request key can prevent duplicate writes. Unsent drafts and pending
browser retry keys last only for the current tab session; saved data is in SQLite.
Use **Refresh stored workspace data** in the header to reload changes made in
another tab. There is no live subscription or multi-user editing coordination.

The real `GET /api/health` endpoint remains `{"status":"ok"}`. This checks server
liveness, not database readiness; database errors are reported separately by the
workspace. Vite still proxies `/api` to `http://127.0.0.1:8000`.

## Requirements and dependencies

Use Windows PowerShell, Node.js 24, `npm.cmd`, and the existing Python 3.14
virtual environment at `backend/.venv`. Activation is unnecessary. The installed
SQLAlchemy/Alembic/FastAPI dependencies work with Python 3.14; no global Python
settings were changed. Dependencies are pinned in `backend/requirements.txt` and
`frontend/package-lock.json`.

Dependencies are already installed in this workspace. Only for a fresh checkout
or changed dependency files, run from the repository root:

```powershell
# Only create the environment if it does not exist.
if (-not (Test-Path backend/.venv/Scripts/python.exe)) { py -3.14 -m venv backend/.venv }
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

No API keys or `.env` file are needed. `.env.example` documents an optional
`DATABASE_URL` environment override. Environment files are not loaded
automatically. The API, migrations, and seed command all use the same variable
when set; otherwise they use the absolute default database path. Never expose
secrets in frontend code or `VITE_` variables.

## Migration and explicit seeding

Run from the project root. Check the current database before applying migrations:

```powershell
Set-Location "C:\Users\Saad\Desktop\portfolio\ai-support-agent"
.\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads
# Only needed when current is behind head, or for an empty database:
.\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

The existing workspace database was inspected at `872fd5de88cd (head)` during
this milestone's resumed verification. No migration, reset, or reseed was
applied to it. Neither migration nor seeding runs at server startup.

For a fresh demo database, explicitly add the four original sample scenarios:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.seed
```

**Seeding is not needed for the existing populated workspace.** It uses stable
IDs and a transaction: existing conversations are skipped entirely, preserving
messages, notes, statuses, handling modes, and events. Existing customers,
orders, and settings are never overwritten. Repeating it adds only missing
sample scenarios and initializes settings only when absent. It does not reset
work. Imported scenario dates and tool outputs are fictional sample data.

Keep the database file when upgrading or restarting. Local databases, SQLite
journals, virtual environments, caches, secrets, and build outputs are ignored;
`.env.example` and migrations belong in version control.

## Start in two VS Code PowerShell terminals

Terminal 1, backend:

```powershell
Set-Location "C:\Users\Saad\Desktop\portfolio\ai-support-agent"
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --reload-dir backend --host 127.0.0.1 --port 8000
```

Terminal 2, frontend:

```powershell
Set-Location "C:\Users\Saad\Desktop\portfolio\ai-support-agent"
npm.cmd --prefix frontend run dev
```

Open <http://127.0.0.1:5173>. Interactive API documentation, validation schemas,
and documented errors are at <http://127.0.0.1:8000/docs>. Stop servers using
`Ctrl+C`. Both servers bind to localhost. Vite uses strict port 5173; stop an old
server in its terminal before starting a replacement. Production deployment and
API routing are outside this milestone.

## Handling and retry rules

Ticket status and handling mode are independent:

| API field | Values | UI labels |
| --- | --- | --- |
| `status` | `open`, `in_progress`, `resolved` | Open, In progress, Resolved |
| `handling_mode` | `ai`, `human`, `awaiting_human` | AI handling, Human handling, Awaiting human attention |

- Public replies require an active ticket under human handling. They are stored
  demo messages, never delivered externally. Internal notes are distinct team
  records, may be added on resolved tickets, and do not replace the public preview.
- Takeover selects human handling and pauses AI responses. Resume switches a
  human-controlled active ticket to AI and records an event, preserving all
  history. It waits for the next customer message and adds no immediate reply.
- Resolved tickets reject public replies, takeover, resume, and simulated incoming
  messages with HTTP 409 until explicitly reopened. Reopening preserves handling
  mode and generates no reply. Repeating the current status/handling is a no-op.
- **Simulate next customer message**, under View activity, stores one fixed
  customer message. Only active AI handling also adds a fixed acknowledgment.
  Human and awaiting-human modes add no automatic reply. This is not an AI service.
- Every mutation requires `Idempotency-Key` (8-128 letters, digits, `.`, `_`, `:`,
  or `-`; UUIDs work). Reuse the same key and payload for a retry, and a new key
  for a new intentional action. The write and saved response commit together.
  Concurrent identical requests produce one message/event. Replays return the
  original response even if newer edits exist; GET again for the latest state.
  A reused key with different content or endpoint returns HTTP 409.

These rules are enforced by the backend, regardless of frontend controls.

## API reference

All paths below begin with `/api`; `{id}` is a conversation ID such as `TKT-1042`.

| Method and path | Behavior |
| --- | --- |
| `GET /health` | Existing application health response |
| `GET /conversations` | Snapshots with customer, order, ordered messages/events; optional `q`, `status`, `handling_mode` filters |
| `GET /conversations/{id}` | One full conversation snapshot |
| `POST /conversations/{id}/messages` | `{ "kind": "reply" or "note", "text": "..." }`; trimmed, 1-5000 characters |
| `PATCH /conversations/{id}/status` | `{ "status": "open" or "in_progress" or "resolved" }` |
| `POST /conversations/{id}/takeover` | Switch to human handling; no body |
| `POST /conversations/{id}/resume` | Resume AI after human handling; no body |
| `POST /conversations/{id}/simulate-customer` | Clearly simulated incoming message; no body |
| `GET /conversations/{id}/activity` | Ordered conversation events |
| `GET /activity` | Recorded events across conversations |
| `GET /settings`, `PUT /settings` | Read or replace the validated support preferences |
| `GET /overview` | Current total, active, AI-handled, awaiting-human, resolved counts and handover IDs |

Search matches customer name/email, ticket/order ID, subject, and preview.
Filters combine. Handling filters exclude resolved tickets. The current Inbox
also filters its loaded snapshot locally. Unknown records return 404; invalid
payloads or missing retry keys return 422; handling or retry-key conflicts return
409; unavailable/locked/unmigrated databases return 503 with recovery guidance.
A migrated empty database returns an empty conversation list and zero metrics.
Missing settings return 404 until explicit seed or a valid settings PUT.

Settings only accept company, support email, supported time zone, unique support
days, same-day opening/closing times, tone, and three escalation preferences.
Unknown fields and credentials are rejected. No authentication is provided;
this API is intended only for this local demo.

## Still simulated or deferred

- AI acknowledgments, carrier/order tool outputs, source policy excerpts, and
  external message delivery remain simulated and visibly labeled.
- Knowledge Base uses separate document fixtures. Search, preview, and simulated
  upload work in memory; uploads reset on refresh. No file ingestion, indexing,
  embeddings, or retrieval service exists yet.
- Historical conversation volume and performance analytics are explicitly
  unavailable. Four imported tickets are not used to invent historical trends.
- Saved support hours, tone, and escalation preferences do not schedule replies,
  route messages, or change the fixed AI simulation.
- Old browser-only settings from the previous milestone are neither imported
  nor deleted; the Settings page now reads SQLite. Unsent drafts are not stored.

## Verification

These commands use separate test databases. A unique workspace temp directory
avoids old Windows temp/cache permission issues without changing their permissions
or deleting existing directories:

```powershell
$testRunPath = Join-Path (Get-Location).Path ('.verification\pytest-' + [guid]::NewGuid().ToString())
if (Test-Path -LiteralPath $testRunPath) { throw 'Test path must be new' }
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider --basetemp $testRunPath
.\backend\.venv\Scripts\python.exe -m pip check
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

The build runs TypeScript checks before producing `frontend/dist/`. Backend tests
apply Alembic migrations to fresh temporary databases and check model/schema
agreement. They cover replies versus notes, paused AI, resume waiting, resolved
restrictions, concurrent retries, persisted request keys, separate sessions,
repeatable seed preservation, settings validation, filters, and current metrics.

With the two normal servers running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:5173/api/health
Invoke-RestMethod http://127.0.0.1:5173/api/overview
```

Resumed verification passed eight backend tests, three frontend tests, lint,
TypeScript, build, and dependency checks. The backend tests emit two third-party
deprecation warnings. Headless Chrome verified acknowledged writes, failed-save
recovery, handling transitions, settings, and browser refresh on a separate
SQLite database. A real backend process restart preserved those records.
Desktop 1366x768 and mobile 390x844/320x568 checks passed, including the details
drawer and composer fit. Browser emulation does not test a physical phone's
software keyboard. Ignored browser artifacts are under `.verification/`.

## Code map

- `frontend/src/api.ts`: API types, UI state mapping, errors, and retry keys.
- `frontend/src/App.tsx`: loaded API snapshots, navigation, and acknowledged writes.
- `frontend/src/components/`: shared shell, Inbox, messages, details, health indicator.
- `frontend/src/pages/`: Overview, Knowledge Base, Agent Activity, Settings.
- `frontend/src/data/`: UI types, settings validation, separate Knowledge Base fixtures.
- `frontend/tests/inbox.test.ts`: API mapping, retry, and settings tests.
- `backend/main.py`: validated API routes and application factory.
- `backend/database.py`, `models.py`: SQLite transactions and SQLAlchemy models.
- `backend/schemas.py`, `service.py`: validation, serialization, handling/idempotency rules.
- `backend/migrations/`, `alembic.ini`: explicit Alembic schema history.
- `backend/seed.py`, `seed_data.json`: repeatable command and original sample scenarios.
- `backend/tests/test_api.py`: isolated migration and persistence tests.
- `design-reference/stitch/`: original exported HTML, screenshots, and design guidance; unchanged.
