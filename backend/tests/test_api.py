import pytest
import concurrent.futures
from fastapi.testclient import TestClient
from backend.app.main import app

# Users in seed:
# u1: Admin (all teams)
# u2: Team Member (team_lead, team_sales)
# u3: Team Member (team_lead only)
# u5: Observer (team_lead)
# u6: Team Member (team_sales)
# u8: Team Member (team_ops)

def test_team_member_cross_team_access_denied(client: TestClient):
    """
    Test: A Team Member reading another team's data is refused with 403.
    u3 belongs to team_lead ONLY, so accessing team_sales or team_ops must return 403.
    """
    # u3 reading team_lead -> OK (200)
    resp_ok = client.get("/api/teams/team_lead/measurables", headers={"x-user-id": "u3"})
    assert resp_ok.status_code == 200

    # u3 reading team_sales -> 403 Forbidden
    resp_forbidden = client.get("/api/teams/team_sales/measurables", headers={"x-user-id": "u3"})
    assert resp_forbidden.status_code == 403

    # u3 reading team_ops -> 403 Forbidden
    resp_forbidden_ops = client.get("/api/teams/team_ops/measurables", headers={"x-user-id": "u3"})
    assert resp_forbidden_ops.status_code == 403

def test_admin_cross_team_access_allowed(client: TestClient):
    """Admin u1 can read all teams."""
    for tid in ["team_lead", "team_sales", "team_ops"]:
        resp = client.get(f"/api/teams/{tid}/measurables", headers={"x-user-id": "u1"})
        assert resp.status_code == 200

def test_observer_write_refused(client: TestClient):
    """
    Test: An Observer write is refused with 403.
    u5 is an Observer on team_lead.
    """
    # 1. Edit score -> 403
    resp_score = client.put(
        "/api/measurables/m1/scores/2026-11-09",
        json={"value": 15.0},
        headers={"x-user-id": "u5"}
    )
    assert resp_score.status_code == 403

    # 2. Create issue -> 403
    resp_issue = client.post(
        "/api/teams/team_lead/issues",
        json={"title": "Observer created issue"},
        headers={"x-user-id": "u5"}
    )
    assert resp_issue.status_code == 403

    # 3. Solve issue -> 403
    resp_solve = client.post(
        "/api/issues/i1/solve",
        json={"resolution_note": "Observer note"},
        headers={"x-user-id": "u5"}
    )
    assert resp_solve.status_code == 403

    # 4. Create To-Do -> 403
    resp_todo = client.post(
        "/api/teams/team_lead/todos",
        json={"title": "Observer todo", "owner_id": "u2"},
        headers={"x-user-id": "u5"}
    )
    assert resp_todo.status_code == 403

    # 5. Start meeting -> 403
    resp_meeting = client.post(
        "/api/teams/team_lead/meetings/start",
        headers={"x-user-id": "u5"}
    )
    assert resp_meeting.status_code == 403

def test_concurrent_make_it_an_issue(client: TestClient):
    """
    Test: Concurrent Make it an Issue requests return one Issue (no duplicates).
    Two or more concurrent requests for the same off-track measurable and week_start.
    """
    payload = {
        "measurable_id": "m1",
        "week_start": "2026-10-26"
    }

    results = []
    def make_request(user_id):
        return client.post(
            "/api/teams/team_lead/issues/make-from-measurable",
            json=payload,
            headers={"x-user-id": user_id}
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(make_request, "u2"),
            executor.submit(make_request, "u3"),
            executor.submit(make_request, "u4"),
            executor.submit(make_request, "u1"),
        ]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    # All should succeed (200)
    for r in results:
        assert r.status_code == 200, r.text

    # All should return the exact same issue ID!
    issue_ids = {r.json()["id"] for r in results}
    assert len(issue_ids) == 1, f"Expected 1 unique issue ID, got: {issue_ids}"

def test_make_it_an_issue_rejects_non_off_track_cells(client: TestClient):
    """Only off-track cells may become issues: on-track and pending are refused."""
    headers = {"x-user-id": "u2"}

    # m1 week 2026-09-14 scored 14 against >= 10 -> on track
    on_track = client.post(
        "/api/teams/team_lead/issues/make-from-measurable",
        json={"measurable_id": "m1", "week_start": "2026-09-14"},
        headers=headers,
    )
    assert on_track.status_code == 400, on_track.text

    # m1 current week 2026-11-09 has no score -> pending
    pending = client.post(
        "/api/teams/team_lead/issues/make-from-measurable",
        json={"measurable_id": "m1", "week_start": "2026-11-09"},
        headers=headers,
    )
    assert pending.status_code == 400, pending.text

def test_make_it_an_issue_rejects_week_outside_window(client: TestClient):
    """A Monday outside the 13-week scorecard window is refused."""
    resp = client.post(
        "/api/teams/team_lead/issues/make-from-measurable",
        json={"measurable_id": "m1", "week_start": "2026-01-05"},
        headers={"x-user-id": "u2"},
    )
    assert resp.status_code == 400, resp.text

def test_make_it_an_issue_requires_monday(client: TestClient):
    """A non-Monday week key fails schema validation with 422."""
    resp = client.post(
        "/api/teams/team_lead/issues/make-from-measurable",
        json={"measurable_id": "m1", "week_start": "2026-10-27"},
        headers={"x-user-id": "u2"},
    )
    assert resp.status_code == 422, resp.text

def test_meeting_lifecycle_and_summary(client: TestClient):
    """Test full meeting lifecycle: start, join, advance sections, rate, end, summary."""
    # u2 starts meeting in team_sales
    start_resp = client.post(
        "/api/teams/team_sales/meetings/start",
        headers={"x-user-id": "u2"}
    )
    assert start_resp.status_code == 200
    meeting_data = start_resp.json()
    meeting_id = meeting_data["id"]
    assert meeting_data["current_section"] == "scorecard"

    # u6 joins
    join_resp = client.post(
        f"/api/meetings/{meeting_id}/join",
        headers={"x-user-id": "u6"}
    )
    assert join_resp.status_code == 200
    assert "u6" in join_resp.json()["attendees"]

    # u2 advances to IDS
    adv1 = client.post(f"/api/meetings/{meeting_id}/advance", headers={"x-user-id": "u2"})
    assert adv1.status_code == 200
    assert adv1.json()["current_section"] == "ids"

    # u2 advances to Conclude
    adv2 = client.post(f"/api/meetings/{meeting_id}/advance", headers={"x-user-id": "u2"})
    assert adv2.status_code == 200
    assert adv2.json()["current_section"] == "conclude"

    # u2 and u6 rate
    rate1 = client.post(f"/api/meetings/{meeting_id}/rate", json={"rating": 9}, headers={"x-user-id": "u2"})
    assert rate1.status_code == 200
    rate2 = client.post(f"/api/meetings/{meeting_id}/rate", json={"rating": 10}, headers={"x-user-id": "u6"})
    assert rate2.status_code == 200

    # Observer u7 trying to rate -> 403
    rate_obs = client.post(f"/api/meetings/{meeting_id}/rate", json={"rating": 5}, headers={"x-user-id": "u7"})
    assert rate_obs.status_code == 403

    # u2 ends meeting
    end_resp = client.post(f"/api/meetings/{meeting_id}/end", headers={"x-user-id": "u2"})
    assert end_resp.status_code == 200
    assert end_resp.json()["status"] == "ended"

    # Fetch summary
    summary_resp = client.get(f"/api/meetings/{meeting_id}/summary", headers={"x-user-id": "u2"})
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["rating"] == 9.5
    assert set(summary["attendee_ids"]) == {"u2", "u6"}

def test_only_facilitator_advances_and_ends(client: TestClient):
    """Even Admins cannot drive a meeting they do not facilitate."""
    start = client.post("/api/teams/team_lead/meetings/start", headers={"x-user-id": "u2"})
    assert start.status_code == 200
    meeting_id = start.json()["id"]

    # u3 is a team member, u1 is a company Admin; neither is the facilitator.
    assert client.post(f"/api/meetings/{meeting_id}/advance", headers={"x-user-id": "u3"}).status_code == 403
    assert client.post(f"/api/meetings/{meeting_id}/advance", headers={"x-user-id": "u1"}).status_code == 403
    assert client.post(f"/api/meetings/{meeting_id}/end", headers={"x-user-id": "u1"}).status_code == 403

    # Ratings are only accepted from attendees, only in Conclude.
    assert client.post(f"/api/meetings/{meeting_id}/rate", json={"rating": 8}, headers={"x-user-id": "u2"}).status_code == 400
    assert client.post(f"/api/meetings/{meeting_id}/advance", headers={"x-user-id": "u2"}).status_code == 200
    assert client.post(f"/api/meetings/{meeting_id}/rate", json={"rating": 8}, headers={"x-user-id": "u2"}).status_code == 400
    assert client.post(f"/api/meetings/{meeting_id}/advance", headers={"x-user-id": "u2"}).status_code == 200

    # u6 is a member of another team and cannot rate a team_lead meeting.
    assert client.post(f"/api/meetings/{meeting_id}/rate", json={"rating": 8}, headers={"x-user-id": "u6"}).status_code == 403
    # u3 can join from their own browser, then rate.
    assert client.post(f"/api/meetings/{meeting_id}/join", headers={"x-user-id": "u3"}).status_code == 200
    assert client.post(f"/api/meetings/{meeting_id}/rate", json={"rating": 8}, headers={"x-user-id": "u3"}).status_code == 200

    assert client.post(f"/api/meetings/{meeting_id}/end", headers={"x-user-id": "u2"}).status_code == 200

def test_latest_ended_meeting_is_available(client: TestClient):
    resp = client.get("/api/teams/team_lead/meetings/latest-ended", headers={"x-user-id": "u2"})
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["status"] == "ended"

def test_meeting_section_timer_advances_in_real_time(client: TestClient):
    """
    APP_NOW is pinned to the seed instant, but the live section timer must
    still run. It is anchored to a real wall-clock timestamp on the server.
    """
    import time

    start = client.post("/api/teams/team_lead/meetings/start", headers={"x-user-id": "u2"})
    assert start.status_code == 200
    meeting_id = start.json()["id"]

    first = client.get(
        "/api/teams/team_lead/meetings/current", headers={"x-user-id": "u2"}
    ).json()["section_elapsed_seconds"]
    time.sleep(1.2)
    second = client.get(
        "/api/teams/team_lead/meetings/current", headers={"x-user-id": "u2"}
    ).json()["section_elapsed_seconds"]
    assert second >= first + 1

    # Advancing resets the section clock.
    adv = client.post(f"/api/meetings/{meeting_id}/advance", headers={"x-user-id": "u2"})
    assert adv.status_code == 200
    assert adv.json()["section_elapsed_seconds"] <= 1

    client.post(f"/api/meetings/{meeting_id}/end", headers={"x-user-id": "u2"})


def test_websocket_requires_team_membership(client: TestClient):
    with client.websocket_connect("/api/meetings/team_lead/ws?user_id=u2") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"

    # u6 belongs to team_sales, not team_lead.
    with pytest.raises(Exception):
        with client.websocket_connect("/api/meetings/team_lead/ws?user_id=u6"):
            pass

    # Missing identity is rejected too.
    with pytest.raises(Exception):
        with client.websocket_connect("/api/meetings/team_lead/ws"):
            pass

