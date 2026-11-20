import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.seeder import seed_database
from backend.app.routers.report import generate_rules_report

SEED_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "seed.json"))


@pytest.fixture()
def fresh_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'report.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    seed_database(seed_file_path=SEED_PATH, db=db)
    yield db
    db.close()
    engine.dispose()


def test_report_matches_seed_answer_key(fresh_db):
    report = generate_rules_report(fresh_db)
    assert report["now"] == "2026-11-11T15:00:00Z"
    assert set(report["teams"]) == {"team_lead", "team_sales", "team_ops"}

    lead = report["teams"]["team_lead"]
    assert len(next(iter(lead["measurable_status"].values()))) == 13
    assert set(lead["todo_completion"]) == {
        "2026-08-17", "2026-08-24", "2026-08-31", "2026-09-07", "2026-09-14",
        "2026-09-21", "2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19",
        "2026-10-26", "2026-11-02", "2026-11-09",
    }

    # The two purposeful boundary To-Dos: t28 lands one minute inside the week,
    # t29 one minute outside it.
    assert lead["todo_completion"]["2026-11-02"] == {
        "due": 10, "done": 9, "rate_percent": 90, "meets_target": True
    }
    assert lead["todo_completion"]["2026-10-26"] == {
        "due": 3, "done": 2, "rate_percent": 67, "meets_target": False
    }
    assert lead["todo_completion"]["2026-08-17"] is None

    assert lead["overdue_todos"] == ["t12", "t31"]
    assert lead["issue_order"] == ["i2", "i1", "i5", "i3", "i4"]

    assert lead["rocks"]["r1"] == {"status": "on_track", "progress_percent": 33}
    assert lead["rocks"]["r2"] == {"status": "off_track", "progress_percent": 13}
    assert lead["rocks"]["r3"] == {"status": "complete", "progress_percent": 100}
    assert lead["rocks"]["r4"] == {"status": "off_track", "progress_percent": 0}

    mt1 = lead["meetings"]["mt1"]
    assert mt1["scorecard_week"] == "2026-10-19"
    assert mt1["issues_solved"] == ["i7"]
    assert mt1["todos_created"] == ["t20"]
    assert mt1["attendee_ids"] == ["u1", "u2", "u3", "u4", "u5"]
    assert mt1["rating"] == 8.0

    mt2 = lead["meetings"]["mt2"]
    assert mt2["scorecard_week"] == "2026-10-26"
    assert mt2["issues_solved"] == ["i6"]
    assert mt2["todos_created"] == ["t30"]
    assert mt2["rating"] == 8.3

    ops = report["teams"]["team_ops"]
    assert ops["todo_completion"]["2026-11-02"] == {
        "due": 1, "done": 1, "rate_percent": 100, "meets_target": True
    }


def test_meeting_status_is_always_closed_week(fresh_db):
    # APP_NOW inside the meeting's reviewed week must not turn a missing score
    # into "pending"; the meeting reviewed an already-closed week.
    report = generate_rules_report(fresh_db, custom_now_str="2026-10-20T15:00:00Z")
    assert report["now"] == "2026-10-20T15:00:00Z"
    assert report["teams"]["team_lead"]["meetings"]["mt1"]["measurable_status"]["m5"] == "off_track"
