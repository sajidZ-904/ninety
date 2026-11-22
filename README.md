# ninety
# Ninety Level 10 Meeting Platform

A working implementation of the Ninety (EOS edition) weekly leadership loop: Measurables, Rocks, To-Dos, Issues, and the Level 10 meeting with real-time multi-browser sync.

**Stack:** Next.js 14 (App Router, TypeScript, shadcn/ui + Tailwind CSS) · FastAPI + SQLAlchemy · PostgreSQL (Alembic migrations; SQLite for tests)

## Setup

```bash
docker compose up --build
```

On boot the backend runs `alembic upgrade head`, loads `seed.json` (idempotent), and starts with `APP_NOW=2026-11-11T15:00:00Z`, `COMPANY_TIMEZONE=America/Chicago`.

- App: http://localhost:3000 (seeded user switcher in the header)
- API + Swagger: http://localhost:8000/docs · Health: http://localhost:8000/health
- Postgres: `localhost:5432` (`ninety_db`); reset with `docker compose down -v`

Without Docker: `python -m venv .venv`, `pip install -r backend/requirements.txt`, set `DATABASE_URL` (defaults to `sqlite:///./ninety.db`), `alembic -c backend/alembic.ini upgrade head`, `python -m backend.app.seeder`, `uvicorn backend.app.main:app --reload`; then `cd frontend && pnpm install && pnpm dev`.

Auth is the seeded user switcher: REST calls send `x-user-id`; the WebSocket handshake uses `?user_id=` (browsers can't set upgrade headers). Every role and team rule is enforced server-side.

## Tests — one unattended command

```bash
./scripts/run_tests.sh          # or: python scripts/test_all.py ; --skip-e2e skips step 3
```

1. **pytest (29 tests):** every 2.6 rule with boundary cases, cross-team 403, observer write 403, concurrent duplicate-free *Make it an Issue*, validation of the source week and off-track status, meeting lifecycle, facilitator-only control, live section timer, WebSocket gating.
2. Regenerates `rules_report.json` from a freshly seeded database and validates its shape.
3. Builds and boots the stack on fresh processes (SQLite e2e DB + FastAPI + Next.js) and runs the **Playwright two-browser test**: facilitator advances Scorecard → IDS → Conclude, the attendee follows live, rates, and both see the summary after a refresh.

**Fixture and clock strategy.** `conftest.py` pins `APP_NOW=2026-11-11T15:00:00Z` before importing the app and recreates + reseeds a dedicated SQLite DB. The rules report builds its own throwaway seeded DB, so it is deterministic at any `APP_NOW`. E2E uses a separate `e2e_ninety.db` (deleted after the run) with one worker so both browsers share a deterministic meeting.

**Failure artifact.** `test-artifacts/failure-trace.zip` is a real Playwright trace from a failing two-browser run (`npx playwright show-trace test-artifacts/failure-trace.zip`). Logs are written to `test-artifacts/`; traces/screenshots/video are retained on failure.

## Rules report

```bash
python backend/rules_report.py                          # JSON to stdout for APP_NOW
python backend/rules_report.py -o rules_report.json     # writes the committed report
python backend/rules_report.py "2026-11-18T15:00:00Z"   # any simulated date
docker compose exec backend python backend/rules_report.py
```

It always seeds a fresh database from `seed.json`, computes every 2.6 value from the data (never hard-coded), and follows the format in the assessment starter README. The committed `rules_report.json` is the output at the default `APP_NOW`.

## Assumptions and known limitations

- Editors (Admin/Team Member) are the only possible To-Do/Issue owners; Observers or non-members are rejected.
- Score edits and issue-priority updates are last-write-wins (optimistic versioning is a documented bonus, not implemented).
- Past-meeting summaries are recomputed from current data; an immutable snapshot table is described in the decision record but not built (the brief asks for the design only).
- Single-node WebSocket manager; horizontal scaling would need Redis pub/sub. Client polling is the degraded-mode safety net.
- Out of scope per the brief: sign-up, email, billing, integrations, private/long-term issues, team/user/KPI/Rock editing, meeting history page.
- Scores are editable for the 13-week window only; `Make it an Issue` targets Measurables (the UI only offers off-track cells).
- The brief's video must be recorded separately; a script is provided in `WALKTHROUGH_SCRIPT.md`.

## AI tools used

- **Qoder (agentic coding assistant):** implementation, audit against the brief, rule cross-checks, test authoring, Docker fixes, and documentation drafting.
- Every computed value in `rules_report.json` was independently recomputed from `seed.json` at multiple `APP_NOW` dates and compared against the generator's output.

Design decisions and tradeoffs: `DECISION_RECORD.md`. Demo script: `WALKTHROUGH_SCRIPT.md`.
