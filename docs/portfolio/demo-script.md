# A 110-second SupportDesk AI recording

[Portfolio overview](../../README.md) | [Architecture](architecture.md) | [Screenshot plan](screenshots.md)

## Prerequisites

Use the existing virtual environment and frontend dependencies. Run one backend
process on `127.0.0.1:8000` and Vite on `127.0.0.1:5173`; commands are in the
[README](../../README.md#run-locally). Wait for backend startup. Do not record keys,
configuration terminals, real customer data, or unrelated browser tabs.

Choose the recording mode before rehearsing:

- **Offline mock:** disclose on screen and in narration: "Offline mock mode:
  model decisions and reply text are simulated; local tools and persistence are
  real." Keep the app's Mock simulation labels visible. This mode needs no key.
- **Existing Gemini configuration:** keep your configured backend terminal. Only
  call it a Gemini recording when that run actually succeeds with Gemini. A key
  being configured is not evidence of a successful request. Manual sends/retries
  can contact Google; this preparation task made no live calls. Do not fall back
  to mock while claiming the recording demonstrates Gemini.

Use fictional policies only. In the staff Knowledge Base explicitly import
[shipping-returns.md](../../demo-fixtures/shipping-returns.md), wait for Ready,
and verify **Document search** returns an excerpt for `returns`. The fixture is
not imported automatically. It describes a 30-day return window and fictional
shipping terms. Do not invent an answer if the current library has no evidence.
In a regular workspace, importing a document adds it to that library; use the
separate workspace below if you want to leave your existing library unchanged.

## Customer and conversation

The existing seed defines Michael Chang as `CUS-1041`, order `ORD-9104`, and
conversation `TKT-1041`. These IDs are read from the sample data, not invented
recording placeholders. Current status/handling may differ from the initial seed.

For a new exchange in the existing thread, open
[Michael's customer chat](http://127.0.0.1:5173/demo/customer?customer=CUS-1041&conversation=TKT-1041),
then **Staff view** in a second tab. Reopen explicitly if resolved; if awaiting a
person, take over first, then Resume AI. If already human-controlled, Resume AI.
Leave all previous messages in place. This starts a new exchange, not an empty
history. **Start or continue order conversation** returns the saved order thread,
including a resolved thread; it is not a reset or "new blank chat" button.

For a genuinely empty recording thread, use the optional isolated preparation
below. It adds `TKT-SHOWCASE-1041` for the same fictional customer and order in a
new recording database, leaving every seeded conversation intact. This is a
one-time developer preparation step, not an application feature. Do not delete
messages or resolved tickets to stage a recording.

## Recording sequence (target 110 seconds)

Have both tabs open to the same ticket, the policy imported, and handling set to
AI. Scenario buttons fill a draft; you still press **Send message**. Wait for each
turn to finish before sending another. Timings below are editing targets, not
promises about response latency. If a run takes longer, pause narration or label
an edit that removes waiting time; never splice in a fabricated successful answer.

| Time | On-screen action | Suggested narration |
| --- | --- | --- |
| 0-10 s | Show the fictional customer banner and the actual provider/mode label. | "This is my local support portfolio demo with fictional store data." Add the explicit mock disclosure above if applicable. |
| 10-30 s | Customer sends **What is your returns policy?** Wait for a reply. Switch to staff Inbox and expand **View sources** on that new reply. | "The assistant searches an uploaded policy. Staff can inspect the saved citation and quoted passage." Show the actual document title and section. Customer chat itself has no structured citation card. |
| 30-45 s | Back in customer chat, send **What is the stored status of my order ORD-9104?** Show the reply when complete. | "This lookup uses Michael's stored sample order. It is not live carrier tracking." Do not narrate a fixed shipping result; use what this run returns. |
| 45-60 s | Open staff **Agent Activity**, select the newest order run for this ticket, and expand **View tool input and result** for `get_order_details`. | "These are recorded tool inputs and results from the run, separate from the seeded history examples." Show the order ID and sample-data qualification. |
| 60-88 s | Customer sends **Please connect me with a person.** Wait for human-attention status. In staff Inbox, choose **Take over from AI**, then send a public reply: **Hi Michael, Alex here. I can help review your question. What would you like me to check?** Return to customer chat to show **Support specialist**. | "The handover pauses AI. A staff member takes control, and their public reply appears in the customer's chat." The reply makes no refund, delivery, or external-action promise. |
| 88-110 s | Staff selects **Resume AI**. Briefly show that it waits without adding a reply. Customer then sends **What is your shipping policy?** Wait for the new reply; show its saved source in staff view if time permits. | "Resuming preserves history and waits for the next customer message. That new message starts the next agent turn." |

If a turn fails, keep the error honest. Use an eligible explicit retry after any
cooldown, or fix the prerequisite and rehearse again. Do not show a seeded AI
sample as the answer to a newly sent question. The real run list, not the collapsed
seeded-history section, is the evidence for new tool execution.

An optional longer cut can show an internal note such as "Demo: review the stored
order with Michael." It remains staff-only. Do not claim a screenshot proves API
privacy; the existing backend tests cover public-field filtering.

## Optional: a separate workspace with an empty thread

Skip this section if continuing `TKT-1041` suits the recording. These commands are
for you to run deliberately; they were not executed against your data during
portfolio preparation. They create a new, ignored folder under `.verification/`
and use only that folder's database/uploads. They never reset the normal database.

1. Stop any server already using ports 8000/5173 with Ctrl+C in its own terminal.
   Keep your original configured backend terminal open and unchanged.
2. Open a **new PowerShell terminal** at the repository root for this offline
   recording. Run the block below only in that new terminal. The mock and storage
   overrides are process-local; no `.env` or original provider setting is edited.

```powershell
$showcaseRoot = Join-Path (Get-Location).Path ('.verification\showcase-' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $showcaseRoot) { throw 'Recording folder must be new' }
New-Item -ItemType Directory -Path $showcaseRoot -ErrorAction Stop | Out-Null
$env:SHOWCASE_ROOT = $showcaseRoot
$env:DATABASE_URL = 'sqlite:///' + ((Join-Path $showcaseRoot 'recording.db') -replace '\\', '/')
$env:UPLOAD_DIR = Join-Path $showcaseRoot 'uploads'
$env:AI_PROVIDER = 'mock'
$env:AI_MODEL = 'mock-support-v1'

.\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect recording database' }
.\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect migration head' }
.\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Recording migration failed' }
# Seed only this newly created recording database.
.\backend\.venv\Scripts\python.exe -m backend.seed
if ($LASTEXITCODE -ne 0) { throw 'Recording seed failed' }
```

3. In the **same recording terminal**, add one empty conversation. The guards
   refuse the normal database, and repeating this block preserves an existing
   recording thread rather than clearing it.

```powershell
@'
import os
from pathlib import Path
from sqlalchemy.engine import make_url
from backend.database import make_engine, write_session
from backend.models import Conversation
from backend.service import add_event, now

root = Path.cwd().resolve()
folder = Path(os.environ['SHOWCASE_ROOT']).resolve()
if folder.parent != root / '.verification' or not folder.name.startswith('showcase-'):
    raise SystemExit('Use the new recording folder from the previous block.')
url = make_url(os.environ['DATABASE_URL'])
if url.drivername != 'sqlite' or Path(url.database).resolve() != folder / 'recording.db':
    raise SystemExit('Refusing to modify a non-recording database.')
engine = make_engine()
try:
    with write_session(engine) as session:
        if session.get(Conversation, 'TKT-SHOWCASE-1041') is None:
            original = session.get(Conversation, 'TKT-1041')
            if original is None or (original.customer_id, original.order_id) != ('CUS-1041', 'ORD-9104'):
                raise SystemExit('Expected fictional seed scenario is missing.')
            timestamp = now()
            ticket = Conversation(
                id='TKT-SHOWCASE-1041', customer_id=original.customer_id,
                order_id=original.order_id, subject='Portfolio demonstration',
                preview='New recording conversation', channel=original.channel,
                priority=original.priority, status='open', handling_mode='ai',
                created_at=timestamp, updated_at=timestamp,
            )
            session.add(ticket)
            session.flush()
            add_event(session, ticket, 'Recording conversation prepared',
                      'Fictional local recording; original histories preserved.')
        session.commit()
    print('Recording thread ready: TKT-SHOWCASE-1041 (existing history preserved).')
finally:
    engine.dispose()
'@ | .\backend\.venv\Scripts\python.exe -
if ($LASTEXITCODE -ne 0) { throw 'Recording conversation preparation failed' }

.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

4. Start `npm.cmd --prefix frontend run dev` in a separate frontend terminal.
   Open [the empty recording chat](http://127.0.0.1:5173/demo/customer?customer=CUS-1041&conversation=TKT-SHOWCASE-1041)
   and use **Staff view**. Explicitly upload the fixture into this recording
   workspace's Knowledge Base. Its library starts empty. Rehearse the sequence
   above with the visible mock disclosure; no Gemini key is needed.
5. To keep this recording history, retain the new folder and its printed/assigned
   path. After recording, stop both servers. Close the special recording terminal
   to discard its environment overrides, then restart your normal servers from
   the original configured terminals. No deletion or reseeding is required.
   To restart the recording later, reuse its exact folder/storage overrides;
   rerunning the first block creates a different new workspace.

## Verification scope and recording readiness

The earlier customer-demo milestone reported passing backend/frontend tests and
isolated two-tab browser checks; see the
[verification record](../development.md#customer-demo-verification). They are
previous results, not newly performed checks. This documentation task checked
implementation claims, source IDs, and relative links, without running Gemini,
changing provider configuration, or recording a new demo. Actual rehearsal,
chosen-provider behavior, screenshots, and the final recording remain your next
steps. Fake-provider checks do not establish live Gemini response quality.
