# Demo Walkthrough Script (~6 minutes)

Setup: `docker compose up --build` (seeded on boot, clock pinned at Wed 2026-11-11 09:00 America/Chicago). Open `http://localhost:3000` in two windows — Window A switches to **Alex Rivera (Facilitator)**, Window B to **Jordan Lee (Team Member)**.

## 1. Overview and identity (0:00–0:40)

Show the header team switcher and the four panels: Scorecard, Rocks, To-Dos, Issues. Both windows use the same demo team; the switcher is the authentication boundary (REST sends `x-user-id`, WebSocket sends `?user_id=`).

## 2. Scorecard statuses and Make it an Issue (0:40–1:50)

In Window A, point at the 13-week grid: green/red boundaries, "—" for the open week (pending), "No Score" for closed weeks with nothing recorded. Click an off-track closed-week cell on a measurable, choose **Make it an Issue**, and show the prefilled Issue with the *Source: measurable / week* badge. Click it again from Window B at the same moment: only one Issue exists — the partial unique index and race-safe insert guarantee it.

## 3. Rocks and To-Dos (1:50–2:40)

Show Rock progress (done milestones ÷ total, rounded half up) and an overdue milestone flipping the Rock to off-track. Show a To-Do past its due date as overdue; one completed stays done. Both windows update via the server snapshot.

## 4. Start the meeting — facilitator control (2:40–3:50)

In Window A click **Start Meeting**: the server opens the single active meeting and broadcasts it. Window B's **Join Live Meeting** button becomes enabled; entering the room auto-joins as attendee. Show the 5 / 60 / 10 agenda with the live per-section timer (business timestamp + real-clock anchor) and the section guide.

In Window B, confirm the facilitator-only controls are absent, and explain the server rejects `advance`/`end` from non-facilitators with 403.

## 5. Live sections (3:50–4:50)

Facilitator clicks **Next Section**; Window B follows within a second (WebSocket push, 1 s reconcile poll as the safety net). In IDS, solve one Issue with a resolution note from Window A; in Window B add a follow-up To-Do from an Issue and show the *oldest first within priority* ordering. Refresh Window B mid-meeting: it rejoins the same section with the same elapsed time.

## 6. Conclude, rate, summary (4:50–5:40)

Advance to Conclude: To-Do recap (done / due) and the rating control. Window A rates 5, Window B rates 4. The facilitator clicks **End Meeting**; both windows switch to the summary — average rating 4.5 (one decimal, half up), attendee list, issues solved, To-Dos created, measurable statuses. Refresh Window B: the same summary loads via `latest-ended`.

## 7. Rules report and tests (5:40–6:20)

```bash
docker compose exec backend python backend/rules_report.py
```

Show it matches the committed `rules_report.json` (generated from a fresh seed, nothing hard-coded), and mention `./scripts/run_tests.sh` — 29 pytest cases, report regeneration, and the Playwright two-browser e2e — plus `test-artifacts/failure-trace.zip` as a real failing trace.
