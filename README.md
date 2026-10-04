# SupportDesk AI

A self-directed customer-support portfolio project with a customer demo chat and
staff workspace. React and TypeScript connect to FastAPI, SQLite persistence,
local document search, and a provider-neutral agent with offline mock and optional
Gemini adapters. Business identities, orders, and shipping data are fictional.

The local app implements public replies, internal notes, human takeover/resume,
document uploads and citations, persisted agent activity, and support settings.
Retrieval uses **SQLite FTS5, not embeddings**, with a keyword fallback. Mock mode
simulates model decisions and text while exercising real local tools and storage.
There is no authentication, live carrier integration, or external message delivery.

## Portfolio

- [Case study](docs/portfolio/case-study.md)
- [90-120 second demo script](docs/portfolio/demo-script.md)
- [Architecture and diagram](docs/portfolio/architecture.md)
- [Freelance portfolio copy](docs/portfolio/portfolio-copy.md)
- [Five screenshot views](docs/portfolio/screenshots.md)

## Run locally

From the repository root, reuse the installed dependencies. Keep the backend
terminal that holds your existing provider configuration; `.env` files are not
automatically loaded and environment variables do not transfer to a new terminal.
These commands do not change your provider selection.

Backend terminal:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --reload-dir backend --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
npm.cmd --prefix frontend run dev
```

- [Customer demo](http://127.0.0.1:5173/demo/customer)
- [Staff Inbox](http://127.0.0.1:5173/)
- [API documentation](http://127.0.0.1:8000/docs)

Customer selection is demo impersonation, not sign-in. Staff APIs are also
unauthenticated: keep this on localhost with fictional data. Vite proxies `/api`
to port 8000. If it reports `ECONNREFUSED`, check the backend terminal and wait for
`Application startup complete` before troubleshooting provider credentials.

## Setup and verification reference

See the [development guide](docs/development.md) for dependency setup, migrations,
explicit seeding, private provider configuration, API details, and test commands.
Follow [AGENTS.md](AGENTS.md) when changing source. Preserve `backend/supportdesk.db`,
private `backend/uploads/`, and local environment files. Startup does not migrate
or seed; an existing populated workspace does not need reseeding.

Previously reported customer-demo verification: **70 backend tests**, **5 frontend
tests**, lint, TypeScript/build, migration checks, and isolated desktop/mobile
browser checks. These were not rerun for the portfolio documentation. This task
checks source claims and documentation links only. No live Gemini call or new
browser verification was performed; offline tests do not establish live model quality.
