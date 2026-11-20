# Decision Record — Ninety Level 10 Platform

## 1. Data model and source links

Issues have `source_measurable_id` (FK, `ON DELETE SET NULL`) + `source_week_start`; To-Dos have `source_issue_id` (FK, `ON DELETE SET NULL`). Manual records keep those columns `NULL`. Weeks are Monday keys in company time (`America/Chicago`), computed as Sunday 23:59:59.999999 local → UTC, so DST boundaries are exact; all timestamps are stored in UTC.

**Tradeoff:** a polymorphic JSON `source {type,id,week}` would support arbitrary sources (bonus Rock/To-Do variants) but loses FK enforcement and partial unique indexes. Explicit relational columns were chosen for integrity and race-free constraints; the bonus variants remain additive later.

## 2. API design

Team-scoped nested REST resources (`/api/teams/{id}/measurables|issues|todos|rocks|meetings`) plus explicit actions (`PUT .../scores/{week}`, `PATCH /issues/{id}/priority`, `POST /issues/{id}/solve`, `POST /meetings/{id}/advance|end|join|rate`). FastAPI dependencies enforce identity (`x-user-id`), team read, team write (Observers rejected), facilitator-only control, and owner eligibility; list endpoints reuse one implementation across both pages. Swagger is served at `/docs`.

**Tradeoff:** a generic RPC-style API would be smaller but less cacheable/idiomatic; nested resources make the team boundary the URL's first-class concept, which the authorization layer mirrors exactly.

## 3. Real-time transport and meeting state ownership

The server owns meeting state: `current_section`, business timestamp `section_started_at` (APP_NOW), and a real wall-clock anchor `section_started_real_at`. A pinned APP_NOW cannot animate a live timer, so elapsed seconds come from the real anchor; clients render server snapshots plus a local stopwatch and re-anchor on every update. Overrun shows "Over Time" and never auto-advances. Mutations broadcast over team-room WebSockets; clients also reconcile every second and fall back to `latest-ended`, so blocked upgrades or dropped sockets degrade to ~1 s sync, and refresh/late join/reconnect reconstructs the exact state. One active meeting per team is a partial unique index; only the facilitator advances/ends.

**Tradeoff:** pure WebSocket sync is instant but fragile behind proxies; pure polling is robust but laggy. The hybrid keeps sub-second updates with a one-second floor. Single-node broadcasts would need Redis pub/sub to scale horizontally.

## 4. Duplicate-free Make it an Issue

Check for an existing unsolved Issue for `(measurable, week)`, insert otherwise; the DB enforces `UNIQUE(source_measurable_id, source_week_start) WHERE solved_at IS NULL`. A racing loser hits `IntegrityError`, rolls back, and returns the winner's Issue (HTTP 200). The exact same rule is covered by an API test firing concurrent requests.

**Tradeoff:** application-level locking serializes requests and adds contention; relying on a partial index is lock-free and correct at any concurrency, at the cost of requiring a database that supports partial indexes (Postgres, SQLite — both used here).

## 5. Preserving past summaries

When a meeting ends, compile the summary and persist an immutable JSON snapshot (`meeting_summaries`: `meeting_id`, `ended_at`, `summary_payload`, `final_hash`). `GET /meetings/{id}/summary` returns the frozen snapshot, so later issue reopens, rating edits, or retroactive score changes cannot rewrite history. An `audit_events` ledger (actor, entity, payload, timestamp) would additionally allow replay-based reconstruction.

**Tradeoff:** snapshots duplicate data and need a schema-version field if summaries evolve; recomputation (what the shipped app does for simplicity) is always consistent with current data but not point-in-time — the brief asks for this design only.
