import json
import os
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, engine, Base
from backend.app.models import (
    Company, User, Team, Membership, Measurable, Score,
    Rock, Milestone, Issue, ToDo, Meeting, MeetingAttendee, MeetingRating
)

def seed_database(seed_file_path: str = "seed.json", db: Session | None = None) -> None:
    """Loads seed data from seed.json. Safe to rerun."""
    close_db_on_exit = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        close_db_on_exit = True

    try:
        if not os.path.isabs(seed_file_path) and not os.path.exists(seed_file_path):
            # check parent directories
            alt_path = os.path.join(os.path.dirname(__file__), "..", "..", seed_file_path)
            if os.path.exists(alt_path):
                seed_file_path = alt_path

        with open(seed_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Company
        comp = data["company"]
        existing_comp = db.query(Company).filter(Company.id == comp["id"]).first()
        if not existing_comp:
            db.add(Company(id=comp["id"], name=comp["name"], timezone=comp.get("timezone", "America/Chicago")))
        else:
            existing_comp.name = comp["name"]
            existing_comp.timezone = comp.get("timezone", "America/Chicago")

        # 2. Teams
        for t in data["teams"]:
            existing_team = db.query(Team).filter(Team.id == t["id"]).first()
            if not existing_team:
                db.add(Team(id=t["id"], name=t["name"]))
            else:
                existing_team.name = t["name"]

        # 3. Users
        for u in data["users"]:
            existing_user = db.query(User).filter(User.id == u["id"]).first()
            if not existing_user:
                db.add(User(id=u["id"], name=u["name"], email=u["email"], role=u["role"]))
            else:
                existing_user.name = u["name"]
                existing_user.email = u["email"]
                existing_user.role = u["role"]

        db.flush()

        # 4. Memberships
        for m in data["memberships"]:
            existing_mem = db.query(Membership).filter(
                Membership.user_id == m["user_id"],
                Membership.team_id == m["team_id"]
            ).first()
            if not existing_mem:
                db.add(Membership(user_id=m["user_id"], team_id=m["team_id"]))

        # 5. Measurables
        for m in data["measurables"]:
            existing_m = db.query(Measurable).filter(Measurable.id == m["id"]).first()
            if not existing_m:
                db.add(Measurable(
                    id=m["id"],
                    team_id=m["team_id"],
                    name=m["name"],
                    owner_id=m["owner_id"],
                    unit=m["unit"],
                    goal=m["goal"]
                ))
            else:
                existing_m.team_id = m["team_id"]
                existing_m.name = m["name"]
                existing_m.owner_id = m["owner_id"]
                existing_m.unit = m["unit"]
                existing_m.goal = m["goal"]

        db.flush()

        # 6. Scores
        for s in data["scores"]:
            existing_s = db.query(Score).filter(
                Score.measurable_id == s["measurable_id"],
                Score.week_start == s["week_start"]
            ).first()
            if not existing_s:
                db.add(Score(
                    measurable_id=s["measurable_id"],
                    week_start=s["week_start"],
                    value=float(s["value"]),
                    updated_at=None,
                    version=1
                ))
            else:
                existing_s.value = float(s["value"])

        # 7. Rocks
        for r in data["rocks"]:
            existing_r = db.query(Rock).filter(Rock.id == r["id"]).first()
            if not existing_r:
                db.add(Rock(
                    id=r["id"],
                    team_id=r["team_id"],
                    title=r["title"],
                    owner_id=r["owner_id"],
                    quarter=r["quarter"],
                    status=r["status"]
                ))
            else:
                existing_r.title = r["title"]
                existing_r.status = r["status"]
                existing_r.owner_id = r["owner_id"]

        db.flush()

        # 8. Milestones
        for ms in data["milestones"]:
            existing_ms = db.query(Milestone).filter(Milestone.id == ms["id"]).first()
            if not existing_ms:
                db.add(Milestone(
                    id=ms["id"],
                    rock_id=ms["rock_id"],
                    title=ms["title"],
                    due_date=ms["due_date"],
                    done=bool(ms["done"])
                ))
            else:
                existing_ms.title = ms["title"]
                existing_ms.due_date = ms["due_date"]
                existing_ms.done = bool(ms["done"])

        # 9. Issues
        for i in data["issues"]:
            created_at = datetime.fromisoformat(i["created_at"].replace("Z", "+00:00"))
            solved_at = datetime.fromisoformat(i["solved_at"].replace("Z", "+00:00")) if i.get("solved_at") else None
            
            src_m_id = None
            src_w_start = None
            if i.get("source"):
                src_m_id = i["source"].get("measurable_id")
                src_w_start = i["source"].get("week_start")

            existing_i = db.query(Issue).filter(Issue.id == i["id"]).first()
            if not existing_i:
                db.add(Issue(
                    id=i["id"],
                    team_id=i["team_id"],
                    title=i["title"],
                    owner_id=i["owner_id"],
                    priority=i.get("priority"),
                    created_at=created_at,
                    solved_at=solved_at,
                    resolution_note=i.get("resolution_note"),
                    source_measurable_id=src_m_id,
                    source_week_start=src_w_start
                ))
            else:
                existing_i.title = i["title"]
                existing_i.priority = i.get("priority")
                existing_i.solved_at = solved_at
                existing_i.resolution_note = i.get("resolution_note")

        db.flush()

        # 10. To-Dos
        for t in data["todos"]:
            created_at = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
            done_at = datetime.fromisoformat(t["done_at"].replace("Z", "+00:00")) if t.get("done_at") else None

            existing_t = db.query(ToDo).filter(ToDo.id == t["id"]).first()
            if not existing_t:
                db.add(ToDo(
                    id=t["id"],
                    team_id=t["team_id"],
                    title=t["title"],
                    owner_id=t["owner_id"],
                    due_date=t["due_date"],
                    done_at=done_at,
                    source_issue_id=t.get("source_issue_id"),
                    created_at=created_at
                ))
            else:
                existing_t.title = t["title"]
                existing_t.owner_id = t["owner_id"]
                existing_t.due_date = t["due_date"]
                existing_t.done_at = done_at

        # 11. Meetings
        for mt in data["meetings"]:
            st_at = datetime.fromisoformat(mt["started_at"].replace("Z", "+00:00"))
            end_at = datetime.fromisoformat(mt["ended_at"].replace("Z", "+00:00")) if mt.get("ended_at") else None

            existing_mt = db.query(Meeting).filter(Meeting.id == mt["id"]).first()
            if not existing_mt:
                db.add(Meeting(
                    id=mt["id"],
                    team_id=mt["team_id"],
                    facilitator_id=mt["facilitator_id"],
                    started_at=st_at,
                    ended_at=end_at,
                    current_section="ended" if end_at else "scorecard",
                    section_started_at=st_at
                ))
            else:
                existing_mt.ended_at = end_at

            db.flush()

            # Attendees
            for att_id in mt.get("attendee_ids", []):
                existing_att = db.query(MeetingAttendee).filter(
                    MeetingAttendee.meeting_id == mt["id"],
                    MeetingAttendee.user_id == att_id
                ).first()
                if not existing_att:
                    db.add(MeetingAttendee(meeting_id=mt["id"], user_id=att_id))

            # Ratings
            for r in mt.get("ratings", []):
                existing_r = db.query(MeetingRating).filter(
                    MeetingRating.meeting_id == mt["id"],
                    MeetingRating.user_id == r["user_id"]
                ).first()
                if not existing_r:
                    db.add(MeetingRating(meeting_id=mt["id"], user_id=r["user_id"], rating=r["rating"]))
                else:
                    existing_r.rating = r["rating"]

        db.commit()
        # db seeded successfully
    except Exception as e:
        db.rollback()
        raise e
    finally:
        if close_db_on_exit:
            db.close()

if __name__ == "__main__":
    seed_database()
