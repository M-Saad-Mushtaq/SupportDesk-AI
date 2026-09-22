# Project guidance

SupportDesk AI is a local customer-support portfolio demo with Inbox, Overview,
Knowledge Base, Agent Activity, and Settings sharing the navy/teal Stitch shell.
Its current milestone adds a provider-neutral agent with optional Gemini to
FastAPI/SQLite persistence and local document ingestion/search. Default mode is
explicit offline mock. Live Gemini verification is pending; external messaging
is not integrated.

## Stack and structure

- `frontend/`: React, TypeScript, Vite. `src/App.tsx` holds loaded API snapshots,
  navigation, and acknowledged mutations; the backend is the source of truth.
- `frontend/src/api.ts`: typed API adapter, error handling, idempotency retry keys.
- `frontend/src/components/`: shell, Inbox, conversation, details/drawer, and real
  backend health indicator. Preserve the existing design and interactions.
- `frontend/src/data/inbox.ts`: UI types, status/handling labels, and search filters.
- `frontend/src/data/workspace.ts`: settings validation and shared UI helpers.
- `frontend/src/documentApi.ts`: document metadata, upload, preview, search, and delete API.
- `frontend/src/data/knowledge-fixtures.json`: archived sample references, not the live library.
- `frontend/src/pages/`: Overview, Knowledge Base, Agent Activity, Settings.
- `frontend/tests/inbox.test.ts`: API mapping, retry-key, and settings tests.
- `frontend/vite.config.ts`: localhost:5173 with `/api` proxy to localhost:8000.
- `backend/`: Python 3.14, FastAPI, SQLAlchemy, Alembic, SQLite.
- `backend/main.py`: app factory and documented API, including unchanged `/api/health`.
- `backend/database.py`, `models.py`: database configuration and persisted entities.
- `backend/schemas.py`, `service.py`: validation and backend handling/idempotency rules.
- `backend/migrations/`, `alembic.ini`: reviewed, explicit Alembic migrations.
- `backend/seed.py`, `seed_data.json`: repeatable explicit seed using the original samples.
- `backend/tests/test_api.py`: fresh migrations, handling, retries, and persistence tests.
- `backend/tests/test_documents.py`: isolated file ingestion, citations, fallback, and cleanup tests.
- `backend/documents.py`, `extraction.py`: private file lifecycle and bounded extraction subprocess.
- `backend/retrieval.py`: replaceable PassageRetriever interface; SQLite FTS5/keyword search.
- `backend/document_api.py`: validated Knowledge Base routes.
- `backend/uploads/`: private generated upload files; ignored and never publicly served.
- `backend/.venv/`: existing local environment; invoke its interpreter directly.
- `backend/requirements.in` and `requirements.txt`: direct and pinned dependencies.
- `backend/supportdesk.db`: default local database, ignored; preserve its data.
- `design-reference/stitch/`: original exports, screenshots, and DESIGN.md; keep unchanged.

## PowerShell commands

Run from the repository root. Use `npm.cmd` on Windows. Reuse the working virtual
environment and dependencies; install only when dependency changes require it:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

Check migration state before applying pending migrations:

```powershell
.\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads
# Run only for pending migrations or a new database:
.\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
# Optional: initialize missing sample scenarios/settings, only when requested/needed:
.\backend\.venv\Scripts\python.exe -m backend.seed
```

Never delete, reset, or automatically reseed an existing database. Startup does
not run migrations or seed. Seed skips existing conversation histories and does
not overwrite customers, orders, or settings. `DATABASE_URL`, when explicitly
set in PowerShell, applies to migrations, seeding, and the server; otherwise all
use the absolute default database path. `.env` is not automatically loaded.

Backend terminal:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --reload-dir backend --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
npm.cmd --prefix frontend run dev
```

Checks (test databases must remain separate from demo data):

```powershell
$testRunPath = Join-Path (Get-Location).Path ('.verification\pytest-' + [guid]::NewGuid().ToString())
if (Test-Path -LiteralPath $testRunPath) { throw 'Test path must be new' }
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider --basetemp $testRunPath
.\backend\.venv\Scripts\python.exe -m pip check
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:5173/api/health
```

The build checks TypeScript. Backend tests run fresh Alembic migrations and schema
checks in temporary databases. Do not use the user's database for mutation tests.
API behavior and errors are documented at `http://127.0.0.1:8000/docs`.

## Rules

- Keep changes focused and explain them simply. Preserve existing work.
- Keep secrets on the backend; never place secrets in frontend code or Vite variables.
- Use mock AI responses until real AI integration is explicitly requested. Backend
  persistence authorization does not authorize LLM calls or external messages.
- Preserve imported frontend designs, the local logo, and visible demo indicator.
- Keep sample fixtures separate from components. Knowledge Base uploads are real
  local files with SQLite metadata. Do not restore simulated upload controls.
- Store customers, orders, conversations, messages, events, and non-sensitive
  settings in SQLite. Unsent drafts may stay in React state. Do not restore the
  old localStorage settings or mock ticket reducer as the source of truth.
- Derive Overview counts and activity history from the same persisted records as
  Inbox. Label unsupported historical analytics and tool simulations clearly.
- Keep status (`open`, `in_progress`, `resolved`) separate from handling mode
  (`ai`, `human`, `awaiting_human`). The UI displays In progress for `in_progress`.
- Enforce all handling rules on the backend: takeover pauses AI; resume preserves
  history and waits for the next customer message; resolved tickets are inactive
  until explicitly reopened. Internal notes remain allowed when resolved.
- Record takeover/resume/status events. Commit every write and its idempotency
  response atomically. Retry the same key/payload; reject key reuse with a different
  request. Replays must not undo newer state or create duplicate messages/events.
- Conversation/settings writes use Idempotency-Key. Document uploads deduplicate
  by SHA-256; deletes are idempotent and require UI confirmation.
- Show successful saves only after API acknowledgment. Keep failed input, offer
  actionable retries, and provide loading, empty, and saving states.
- Keep the conversation readable: 220px navigation, 280px list, flexible chat,
  300px details on wide screens. At 1366px use a details drawer; on mobile show
  one panel at a time. Collapse observable tool results under View activity.
- Do not introduce compliance claims, invented AI confidence scores, or latency promises.
- Reuse the local virtual environment; do not change global Python settings.
- Keep `.env.example` tracked and secrets, database files/journals, and build outputs ignored.
- Bind servers to localhost. Do not add Docker, authentication, paid services,
  real LLM calls, agent frameworks, external messaging, or deployment unless requested.

## Document ingestion and search rules

- Supported uploads: text-based PDF, TXT, and Markdown (.md), maximum 10 MB.
  Validate server-side, generate storage filenames, and check path containment.
- Default private storage is `backend/uploads/`; optional `UPLOAD_DIR` must stay
  outside the frontend and be ignored by Git. Move existing copies when changing
  the folder. Never serve or execute uploads as HTML/scripts.
- Extract in the bounded local subprocess: 30 seconds, 200 PDF pages, 2 million
  text characters, 10 MB decoded page-content limit. No OCR. No extractable PDF
  text means `needs_ocr`; partial image-only pages get an explicit warning.
- Preserve PDF page numbers and Markdown headings. Split passages within those
  boundaries (target 1,200 characters, roughly 180 overlap). Show source excerpts
  and locations, never fabricated AI answers or confidence scores.
- Use the new Alembic revision `b7139a42c801`; do not rewrite applied migrations.
  It adds documents/chunks and optional FTS5 plus synchronization triggers.
  Alembic reflection excludes FTS shadow tables, which the migration owns.
- Label retrieval Document search. Tokenize and bind user input; never pass raw
  query syntax to SQL/FTS. Use parameterized keyword fallback if FTS5 is absent.
  Keep retrieval behind PassageRetriever for future embedding integration.
- Failed/OCR files stay recorded; duplicate uploads return the existing status.
  Delete and re-upload to retry. Stale processing (90 seconds) becomes Failed
  on startup/document reads; pending UI records poll every 3 seconds.
- Confirmed deletion removes files, chunks, FTS entries, and metadata. Persist
  `deleting` before file cleanup so interrupted deletion can resume safely.
  Never report success until cleanup completes; keep errors actionable.
- Use isolated upload directories AND databases for tests. Existing Inbox
  records and source references must remain intact through migrations.


## Agent integration rules

- `backend/agent/types.py`: application-owned model/tool contracts; `gemini.py`:
  official Google SDK adapter only; `fake.py`: offline mock/test provider;
  `runner.py`: bounded orchestration; `tools.py`: validated local tools;
  `api.py`: test-message, safe provider status, runs and explicit retry endpoints.
- `frontend/src/agentApi.ts`, `components/TestCustomer.tsx`, and Agent Activity
  expose persisted runs; `ConversationHistory.tsx` separates seeded examples.
- Migration head is `c901bfe20a13`, adding handling revision, message origin,
  agent_runs, and agent_tools. Preserve earlier migrations, SQLite data, uploads,
  and local .env files. Check current/heads before upgrade; never auto-reseed.
- Real integration is authorized, but this milestone explicitly forbids live
  API calls during implementation. Keep fake-provider/SDK-stub tests offline.
  Do not enable billing, buy credits, switch providers as fallback, or print keys.
- AI_PROVIDER defaults to mock; Gemini requires backend-only GEMINI_API_KEY,
  AI_MODEL (documented gemini-2.5-flash), and GEMINI_FREE_TIER_CONFIRMED=true after
  the user verifies an unpaid project. The flag cannot verify Google billing.
  .env files are NOT auto-loaded. README contains private PowerShell setup.
- Configuration alone is unverified. Mark connection verified only after an
  actual successful provider request; show safe missing-key/quota/error states.
- Only public messages (including human replies) enter bounded context; exclude
  internal notes. Pass settings/tone and treat all customer/document/tool text as
  untrusted. Never persist private thoughts or opaque provider signatures.
- Validate policy citation IDs and exact quotes against run retrieval; preserve
  excerpts with the saved reply. Order access is server-scoped to the current
  customer and always labeled stored sample shipping data, not live tracking.
- Public API customer messages persist before generation. AI runs only while
  active and AI-handled. Human/awaiting-human stores without a run; resolved
  requires reopening. Resume waits for the next message.
- One active turn per conversation. Reject new AI-mode messages mid-turn with
  409 and retain UI drafts. Handling/status revisions invalidate in-flight work,
  including takeover then resume. Agent handover plus truthful acknowledgement
  commit together and stop the turn. No ordinary AI reply follows handover.
- Writes and retry responses are atomic. No write transaction spans provider
  I/O. Cache successful tool outcomes by run and arguments. SDK auto-execution
  and automatic retry are disabled. Explicit retries obey attempt/cooldown limits
  and reject stale customer/handling context. Preserve attempt metadata.
- Single backend process only: startup marks pending/running turns interrupted
  without silently repeating provider calls. Review and retry manually. No worker
  fleet, agent framework, external delivery, or deployment.
- Limits in backend/.env.example bound requests, tools, context, output, time,
  and attempts. Whole continuation messages stay paired inside the adapter.
- Never fabricate usage, cost, confidence, historical metrics, or model quality.
  Show provider-reported usage only; label mock runs and seeded activity clearly.
- `backend/tests/test_agent.py` uses real isolated SQLite/tools plus fake models;
  `test_gemini_adapter.py` uses a stub SDK transport. Run them with the full
  existing suite, frontend lint/tests/build, and isolated browser checks. Fake
  tests prove application rules, not live model quality or prompt-injection immunity.
