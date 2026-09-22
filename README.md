# SupportDesk AI

A local customer-support portfolio demo using React, TypeScript, Vite, FastAPI,
SQLAlchemy, Alembic, and SQLite. The existing navy/teal Stitch workspace includes
Inbox, Overview, Knowledge Base, Agent Activity, and Settings. AI defaults to
explicit offline mock mode. Optional Gemini integration is implemented but live
verification is pending; no live API calls were made during implementation.
No customer messages are delivered externally.

## What persists

The default database is `backend/supportdesk.db`. Customers, orders,
conversations, public replies, internal notes, ticket status, handling mode,
activity events, non-sensitive support settings, document metadata, extracted text,
passages, agent runs, tool results, and reply citation snapshots are stored there. Original uploads are stored privately under
`backend/uploads/`. Saved
changes survive browser refresh and backend restart. Overview counts and
handover lists come from the same stored conversations as Inbox; Agent Activity
separates actual agent runs from original sample conversation events. Overview links open the corresponding conversation.

The frontend waits for API acknowledgment before showing success. It provides
loading, empty, saving, and actionable error states. Failed saves retain the
input for retry. After an uncertain network failure, retry the same action so
the existing request key can prevent duplicate writes. Unsent drafts and pending
browser retry keys last only for the current tab session; saved data is in SQLite.
The workspace polls while runs are active and refreshes periodically. The header
refresh button is also available. There is no multi-user editing coordination.

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

Mock mode needs no key or `.env` file. `backend/.env.example` documents AI limits and an optional
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

The current schema head is `c901bfe20a13` (agent runs and handling revisions).
Previously applied migrations `872fd5de88cd` and `b7139a42c801` are unchanged. A private backup
was made under `.verification/`, and every pre-existing customer, order, ticket,
message, event, setting, and retry record was checked unchanged afterward.
Neither migration nor seeding runs at server startup.

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
$env:AI_PROVIDER = 'mock' # Default; optional Gemini setup below
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

## Knowledge Base: local ingestion and document search

Choose a file, select **Upload document**, then review its processing status and
extracted preview. **Document search** returns passages with clickable document
citations. It does not produce AI answers. The old simulated upload control has
been removed; a new library starts empty and no sample documents are auto-imported.

Supported files and limits:

- Text-based `.pdf`, `.txt`, and `.md`, up to **10 MB (10,485,760 bytes)** per file.
  File extension/content type are validated server-side; PDFs need a PDF header.
- TXT/Markdown support UTF-8 (with or without BOM) and UTF-16 with a BOM. Binary
  control characters, undecodable text, and empty documents fail with guidance.
- PDF extraction uses pypdf in a separate local process, with a **30-second**
  timeout, **200-page** cap, **2 million extracted characters**, and a **10 MB
  decoded page-content** cap. Complex PDFs may require splitting or re-exporting.
- PDF page numbers and Markdown `#` headings are retained. Plain text preview
  does not execute or render uploaded HTML/scripts. Original PDFs are not served.
- A PDF without extractable text is **Requires OCR**, never Ready. In a mixed PDF,
  searchable pages are kept and omitted page numbers are reported as a warning.
  OCR is outside this milestone. PDF columns, tables, and reading order can be
  imperfect; consult the [pypdf extraction limitations](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).

Storage and lifecycle:

- Files use generated UUID filenames in `backend/uploads/`, outside the frontend.
  Client filenames are display metadata only. SHA-256 hashes identify identical
  content, including concurrent uploads and retries; the existing record is returned.
- Metadata, original extracted segments, status, and passages persist in SQLite.
  Statuses are Processing, Ready, Requires OCR, Failed, and Deletion pending.
- Interrupted processing older than **90 seconds** is marked Failed on startup
  or the next document read/upload. The UI polls pending records every 3 seconds.
  Failed/OCR records retain their file for inspection; delete and re-upload a
  corrected document to retry. The same unchanged file otherwise returns its
  existing status. No background queue, OCR, or external service is involved.
- **Delete document** opens a confirmation dialog. Confirmation removes the
  stored copy, metadata, passages, and FTS entries. The original file selected on
  your computer is untouched. Interrupted cleanup remains Deletion pending and
  is retried on startup/document reads or a repeated Delete. Failed deletion does
  not show success. Keep the database and upload folder together when backing up.

The optional storage override applies only to the backend:

```powershell
# Optional; keep this location private and excluded from Git.
$env:UPLOAD_DIR = 'C:\Users\Saad\Desktop\portfolio\ai-support-agent\backend\uploads'
```

Do not change `UPLOAD_DIR` without moving the existing stored copies to the new
location. The frontend directory is rejected as a storage root. `.env` files are
not loaded automatically. Uploaded files, databases, secrets, dependencies, and
build outputs are ignored; `.env.example` is retained.

Retrieval behavior:

- Passages target 1,200 characters with about 180 characters of overlap, preferring
  paragraphs/sentences/word boundaries. They never cross PDF pages or Markdown
  sections, so each result has a source location.
- This Python SQLite build supports **FTS5**. The new migration installs a full-text
  index and synchronization triggers. Search ranks matching passages using FTS5;
  scores are not exposed as confidence percentages. See [SQLite FTS5](https://www.sqlite.org/fts5.html).
- If FTS5 is unavailable during migration, the app falls back to parameterized,
  escaped keyword substring matching. The actual mode is shown under Advanced
  search details. Fallback ordering follows passage IDs, lacks FTS relevance, and
  SQLite case folding is limited for non-ASCII text.
- Input is converted to at most 16 distinct word tokens joined with AND. Raw SQL
  and unrestricted FTS syntax are not accepted. Empty queries, punctuation-only
  queries, and no matches have explicit messages. The UI shows up to 20 excerpts
  (API limit up to 50). This is keyword retrieval, without synonyms, semantics,
  vectors, embeddings, or generated answers. Large libraries have no pagination yet.
- Retrieval is behind `PassageRetriever` in `backend/retrieval.py`; future retrieval
  implementations can return the same passage/citation structure to the UI.

Knowledge Base endpoints (interactive schemas and errors are also in `/docs`):

| Method/path | Request and result |
| --- | --- |
| `POST /api/documents` | Multipart `file`; returns document status and `duplicate`. Inspect status: a stored Failed/OCR record is not successful extraction. |
| `GET /api/documents` | Optional filename/title `q` and `status` filters; metadata list. |
| `GET /api/documents/{id}` | Extracted plain-text segments with PDF pages/Markdown sections. |
| `GET /api/documents/search` | `q`, optional `document_id`, `limit` 1-50; excerpts, citations, mode, and empty/no-match message. |
| `DELETE /api/documents/{id}` | Call after confirmation; idempotent cleanup, including retries after a lost response. |

Document uploads use content-hash deduplication instead of `Idempotency-Key`;
deletes are naturally idempotent. Errors: 413 oversized, 415 unsupported type or
invalid PDF header, 422 invalid/missing input, 404 missing preview, 409 document
still processing/deleting, and 503 database/storage cleanup failure. Upload
processing failures are persisted as Failed/Requires OCR with useful errors in
the returned document. The UI retains file selections after request failure.

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
- **Send test customer message** stores your text first, then starts a bounded
  agent turn only in active AI handling. Human/awaiting-human stores the message
  without a run. The old `/simulate-customer` endpoint remains an explicitly
  fixed legacy simulation for compatibility; the UI uses the new endpoint.
- Every conversation/settings mutation requires `Idempotency-Key` (8-128 letters, digits, `.`, `_`, `:`,
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

- Default mock responses are deterministic examples. Gemini is opt-in; live
  connectivity, model quality, and live resistance to instruction attacks are
  unverified. Fake-provider tests cannot establish those properties.
- Orders and carrier updates are stored sample data, never live tracking.
  Human replies and handover acknowledgements are saved locally, not delivered.
- Original seeded AI messages/policy excerpts remain labeled samples. New agent
  citations reference actual retrieved uploads with saved historical excerpts.
- Historical analytics remain unavailable; no invented confidence, costs, or
  token counts. No OCR, embeddings, refunds, external messaging, authentication,
  billing integration, or deployment is included.
- Settings inform new model turns; support hours do not run a scheduler. Mock
  mode remains a simple deterministic test provider, not a real support agent.
- Unsent drafts are local to the tab; saved state is in SQLite.

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
- `frontend/src/data/`: UI types and settings validation; old document fixtures are
  retained as reference data but are no longer loaded into the Knowledge Base.
- `frontend/tests/inbox.test.ts`: API mapping, retry, and settings tests.
- `backend/main.py`: validated API routes and application factory.
- `backend/database.py`, `models.py`: SQLite transactions and SQLAlchemy models.
- `backend/schemas.py`, `service.py`: validation, serialization, handling/idempotency rules.
- `backend/migrations/`, `alembic.ini`: explicit Alembic schema history.
- `backend/seed.py`, `seed_data.json`: repeatable command and original sample scenarios.
- `backend/tests/test_api.py`: isolated migration and Inbox persistence tests.
- `backend/tests/test_documents.py`: isolated ingestion, retrieval, and cleanup tests.
- `backend/documents.py`, `extraction.py`: private file lifecycle and local extraction.
- `backend/retrieval.py`: overlapping passages and the replaceable retrieval interface.
- `backend/document_api.py`, `frontend/src/documentApi.ts`: Knowledge Base API contracts.
- `design-reference/stitch/`: original exported HTML, screenshots, and design guidance; unchanged.

## Knowledge Base verification and Git checkpoint

A local Git repository was initialized with the configured identity. Checkpoint
`2fd5364` preserves the source before ingestion implementation. Nothing was pushed.

At the Knowledge Base checkpoint, the suite passed **25 backend tests** and **3 frontend tests**, frontend
lint, TypeScript/build, dependency checks, and Alembic model/schema agreement.
Backend tests use isolated databases/upload folders and fresh migrations. They
cover valid PDF/TXT/Markdown, unsupported and oversized files, duplicate races,
empty/scanned/corrupt PDFs, page/section citations, safe queries, keyword fallback,
chunking, persistence, extraction timeout, interrupted processing/deletion, and
existing Inbox rules. Two third-party test-client deprecation warnings remain.

Headless Chrome checked real file selection/upload, duplicates, failed-upload
retry, extracted previews, citations, deletion cancel/confirm/failure/retry,
scanned-PDF errors, filters, empty/no-match search, browser refresh persistence,
and Inbox takeover/resume. Desktop 1366x768 and mobile 390x844/320x568 layouts
passed. Files and search also survived an actual test-backend process restart.
Browser files stayed in `.verification/`; no test documents were inserted into
the normal workspace library.


## Agent integration: configuration and zero-spend use

Checkpoint `646c131` preserved the completed Knowledge Base before this milestone.
The official `google-genai` SDK is pinned in the existing environment. No live
Gemini request, billing change, secret-file change, reseed, or remote push is
part of setup. This application cannot inspect or enforce your Google billing
account: **use an unpaid free-tier project and never enable billing**.

As checked on September 19, 2026, Google's [pricing page](https://ai.google.dev/gemini-api/docs/pricing)
lists a free API tier for **`gemini-2.5-flash`**. It supports
[function calling](https://ai.google.dev/gemini-api/docs/function-calling).
Availability and [quotas](https://ai.google.dev/gemini-api/docs/rate-limits) vary
by project/model; inspect your active limits in AI Studio. If no free quota is
available, keep mock mode or wait. Never enable billing to get this demo working.
Google's free-tier pricing states that content can be used to improve products:
use **fictional customer text and non-sensitive test documents only**. Relevant
public history, configured support preferences, order results, and document
excerpts are sent to Google only when you explicitly enable Gemini and send a
new test message or manually retry a failed run. Internal notes are excluded.

Configure privately in **backend Terminal 1**, from the repository root:

```powershell
# In Google AI Studio, select/create an unpaid project and create an API key.
# Check its free quota and leave billing disabled. Never paste the key in chat.
$geminiSecret = Read-Host 'Gemini API key (hidden)' -AsSecureString
$geminiPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($geminiSecret)
try { $env:GEMINI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($geminiPointer) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($geminiPointer) }
Remove-Variable geminiSecret, geminiPointer
$env:AI_PROVIDER = 'gemini'
$env:AI_MODEL = 'gemini-2.5-flash'
$env:GEMINI_FREE_TIER_CONFIRMED = 'true'
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --reload-dir backend --host 127.0.0.1 --port 8000
```


See Google's [private API-key setup](https://ai.google.dev/gemini-api/docs/api-key).
The key above lasts for this PowerShell process and its child server; it is not
written to a file or command history. Do not print environment variables. Local
`.env` files are preserved but **not automatically loaded**. Restart the backend
after configuration changes. Keep all credentials out of Vite variables and Git.
`GEMINI_FREE_TIER_CONFIRMED=true` is your explicit acknowledgment, not a billing
check. The provider label remains **not yet verified** until a request succeeds;
a key alone never establishes connectivity. Failed requests never silently fall
back to mock or another provider. Return to offline mode with:

```powershell
$env:AI_PROVIDER = 'mock'
$env:AI_MODEL = 'mock-support-v1'
# Restart the backend using the normal localhost command.
```

Terminal 2 remains:

```powershell
npm.cmd --prefix frontend run dev
```

### Manual tests after private Gemini configuration

1. Upload a fictional `returns.md` through Knowledge Base, for example:
   `# Returns` followed by `Unused items may be returned within 30 days with proof of purchase.`
2. Open Michael's active conversation (or take over another active ticket and
   Resume AI). Expand **Send test customer message** and ask "What is the returns
   policy?" Review the pending/completed/error state, reply, **View sources**, and
   Agent Activity search inputs/results. Quotes must match the uploaded passage.
3. Ask "What is the stored status of my order ORD-9104?" in Michael's conversation.
   The reply must label this sample stored information, not live carrier tracking.
   Asking for Sarah's `ORD-8492` must not expose her order.
4. Ask "Please connect me with a person." Expect awaiting-human handling and a
   local acknowledgement, with one recorded handover. Further customer messages
   are stored without AI. Take over, add a note/public reply, then Resume AI:
   history is retained and no response is generated until the next new message.
5. Review actual provider/model, duration, reported tokens, tool results, and
   saved sources in Agent Activity. Refresh/restart to check persistence. With a
   failed/quota-limited run, review the error, wait for the displayed time, and
   select **Retry agent turn** explicitly. Do not enable billing or repeatedly
   retry exhausted free quota. Live quality and connectivity remain pending until
   you perform these tests yourself.

### Agent behavior, limits, and extension points

`backend/agent/types.py` owns provider-neutral request/result/tool/session types.
`gemini.py` alone converts Google SDK objects and errors, pairs function calls
with results, and retains opaque continuation signatures in memory. Private
thought text/signatures never enter the activity database or UI. `fake.py` is
an offline scriptable provider. `runner.py` owns orchestration; `tools.py` owns
validated tools, reusing existing handling and retrieval services. A future
provider needs an adapter, selection in `AgentRunner.provider()`, and contract
tests; application/Inbox/tool contracts need not change.

- Public customer/AI/human replies form bounded recent context. Internal notes
  are excluded. Settings and evidence are separated from application rules;
  customer/doc/tool content is untrusted data. Model claims are not proof of a
  completed action. Handover is acknowledged by application code only after its
  state/event transaction succeeds. No other external actions exist.
- Policy answers need source IDs retrieved during that run and exact quote
  matches. Order answers need a successful customer-scoped lookup. Unsupported
  or malformed outputs are not published. Excerpts stay with historical replies
  after document deletion. Citation validation checks provenance and quotes; it
  is not a semantic proof of every sentence. Review live answers before relying
  on them; offline tests are not a live model quality evaluation.
- Default bounds: 16 whole public messages, 24,000 context characters (including
  tool continuations), 1,024 output tokens/request, 4 requests, 6 tool calls,
  20 seconds/request, 60 seconds/turn, and 3 total attempts including explicit
  retries. Validated overrides are in `backend/.env.example`. Whole continuations
  stay paired; oversize context fails rather than trimming function metadata.
- Automatic SDK function execution/retries are disabled. Quota/connection/tool
  failures preserve the incoming message and expose an actionable run error.
  Retry delays default to 60 seconds for quota errors and are capped at 24 hours
  for malformed/extreme provider delays. An explicit retry can make another API
  request; previous attempt metadata and successful tool results are retained.
- One active run per conversation is enforced in SQLite. A second customer
  message during an AI turn gets 409 **without being saved**; its UI draft is
  retained. Human handling can accept incoming messages during an invalidated
  turn. A handling/status revision prevents an old response from publishing
  after takeover/resume or resolve/reopen, even when the final mode matches.
- Idempotency keys prevent duplicate incoming messages, runs, replies, and
  handovers. Tool results deduplicate within a run, including explicit retries.
  Writes use short transactions; no SQLite write transaction spans model I/O.
- **Run one backend process (no workers)**. Startup marks interrupted active
  turns for review and never automatically replays an uncertain provider call.
  Explicit retry is allowed only while handling/customer context is still current.
  Hot reload can interrupt a turn; avoid source edits during a live request.

New endpoints (all prefixed `/api`):

| Endpoint | Behavior |
| --- | --- |
| `GET /ai/status` | Safe provider configuration/last request status, no live probe |
| `POST /conversations/{id}/customer-messages` | `{ "text": "..." }`, 1-3,000 trimmed characters; Idempotency-Key required; returns saved snapshot and pending run ID |
| `GET /agent/runs` | Latest 200 runs by default; optional conversation_id/status/limit (max 500) |
| `GET /agent/runs/{id}` | Actual run, attempts, safe tool inputs/results, reported usage |
| `POST /agent/runs/{id}/retry` | Explicit bounded retry; Idempotency-Key required; 409 for stale/finished work, 429 while cooling down |

Run the checks in the verification section using new temporary test directories.
All agent tests use a fake provider or SDK stub transport, isolated SQLite files,
and temporary uploads. They exercise citation validation, missing evidence,
customer isolation, handover, concurrency, stale reply cancellation, retries,
limits, errors, public-only context, persistence, and interrupted-run recovery.


### Completed agent milestone verification

The complete current suite passes **63 backend tests** and **4 frontend tests**,
frontend lint, TypeScript/production build, `pip check`, and Alembic schema
agreement. Three third-party deprecation warnings remain (Starlette/httpx,
AnyIO, and the Google SDK on Python 3.14); they do not fail the checks.

Headless Chrome verified mock policy citations, customer-scoped order lookup,
handover, human-only incoming messages, resume waiting, individual handling
state, actual run filters/timeline, retained input and retry after a network
failure, browser refresh, and the Vite health proxy. Layout checks passed at
1366x768, 390x844, and 320x568 with no page-level horizontal overflow and the
composer within the viewport. A physical phone keyboard was not tested.
Actual backend process restart preserved the isolated test conversations,
messages, citations, runs, tool results, and documents unchanged.

Migration `c901bfe20a13` is applied to the existing workspace database. A private
backup is under `.verification/pre-agent-802f5ec7af4840eb97a7c98330c3f2d8.db`.
Every pre-existing table value and uploaded file hash was compared unchanged
afterward. No seed command was run against the existing workspace. Browser
artifacts and all test files/databases remain ignored under `.verification/`.
Live Gemini calls, connectivity, model quality, and live injection resistance
remain deliberately unverified. No billing or paid service was enabled.
