from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    ForeignKey, Table, CheckConstraint, Index, UniqueConstraint, JSON, Text
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    timezone = Column(String, nullable=False, default="America/Chicago")

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False) # admin, team_member, observer

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'team_member', 'observer')", name="check_user_role"),
    )

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")

class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)

    memberships = relationship("Membership", back_populates="team", cascade="all, delete-orphan")
    measurables = relationship("Measurable", back_populates="team", cascade="all, delete-orphan")
    rocks = relationship("Rock", back_populates="team", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="team", cascade="all, delete-orphan")
    todos = relationship("ToDo", back_populates="team", cascade="all, delete-orphan")
    meetings = relationship("Meeting", back_populates="team", cascade="all, delete-orphan")

class Membership(Base):
    __tablename__ = "memberships"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    team_id = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)

    user = relationship("User", back_populates="memberships")
    team = relationship("Team", back_populates="memberships")

class Measurable(Base):
    __tablename__ = "measurables"

    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    unit = Column(String, nullable=False)
    goal = Column(JSON, nullable=False) # e.g. {"type": "at_least", "value": 10}

    team = relationship("Team", back_populates="measurables")
    owner = relationship("User")
    scores = relationship("Score", back_populates="measurable", cascade="all, delete-orphan")

class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    measurable_id = Column(String, ForeignKey("measurables.id", ondelete="CASCADE"), nullable=False)
    week_start = Column(String, nullable=False) # Monday YYYY-MM-DD
    value = Column(Float, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    version = Column(Integer, nullable=False, default=1) # Optimistic locking bonus

    __table_args__ = (
        UniqueConstraint("measurable_id", "week_start", name="uq_measurable_week"),
    )

    measurable = relationship("Measurable", back_populates="scores")

class Rock(Base):
    __tablename__ = "rocks"

    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    quarter = Column(String, nullable=False)
    status = Column(String, nullable=False) # on_track, off_track, complete

    __table_args__ = (
        CheckConstraint("status IN ('on_track', 'off_track', 'complete')", name="check_rock_status"),
    )

    team = relationship("Team", back_populates="rocks")
    owner = relationship("User")
    milestones = relationship("Milestone", back_populates="rock", cascade="all, delete-orphan")

class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(String, primary_key=True)
    rock_id = Column(String, ForeignKey("rocks.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    due_date = Column(String, nullable=False) # YYYY-MM-DD
    done = Column(Boolean, nullable=False, default=False)

    rock = relationship("Rock", back_populates="milestones")

class Issue(Base):
    __tablename__ = "issues"

    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    priority = Column(Integer, nullable=True) # 1 to 5, or None
    created_at = Column(DateTime, nullable=False)
    solved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)
    
    # Source link
    source_measurable_id = Column(String, ForeignKey("measurables.id", ondelete="SET NULL"), nullable=True)
    source_week_start = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("priority IS NULL OR (priority >= 1 AND priority <= 5)", name="check_issue_priority"),
        # Partial unique index: an unsolved issue for a given measurable + week_start cannot be duplicated!
        Index(
            "uq_unsolved_measurable_issue",
            "source_measurable_id",
            "source_week_start",
            unique=True,
            postgresql_where=Column("solved_at").is_(None),
            sqlite_where=Column("solved_at").is_(None),
        ),
    )

    team = relationship("Team", back_populates="issues")
    owner = relationship("User")
    source_measurable = relationship("Measurable")
    todos = relationship("ToDo", back_populates="source_issue")

class ToDo(Base):
    __tablename__ = "todos"

    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    due_date = Column(String, nullable=False) # YYYY-MM-DD
    done_at = Column(DateTime, nullable=True)
    source_issue_id = Column(String, ForeignKey("issues.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)

    team = relationship("Team", back_populates="todos")
    owner = relationship("User")
    source_issue = relationship("Issue", back_populates="todos")

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    facilitator_id = Column(String, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    current_section = Column(String, nullable=False, default="scorecard") # scorecard, ids, conclude, ended
    section_started_at = Column(DateTime, nullable=False)
    # Real wall-clock anchor for the live section timer. APP_NOW is fixed for
    # deterministic business rules, so elapsed time cannot be derived from it.
    section_started_real_at = Column(DateTime, nullable=True)

    __table_args__ = (
        # One active meeting per team, enforced at the database layer.
        Index(
            "uq_active_meeting_per_team",
            "team_id",
            unique=True,
            postgresql_where=Column("ended_at").is_(None),
            sqlite_where=Column("ended_at").is_(None),
        ),
    )

    team = relationship("Team", back_populates="meetings")
    facilitator = relationship("User")
    attendees = relationship("MeetingAttendee", back_populates="meeting", cascade="all, delete-orphan")
    ratings = relationship("MeetingRating", back_populates="meeting", cascade="all, delete-orphan")

class MeetingAttendee(Base):
    __tablename__ = "meeting_attendees"

    meeting_id = Column(String, ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    meeting = relationship("Meeting", back_populates="attendees")
    user = relationship("User")

class MeetingRating(Base):
    __tablename__ = "meeting_ratings"

    meeting_id = Column(String, ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    rating = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 10", name="check_meeting_rating"),
    )

    meeting = relationship("Meeting", back_populates="ratings")
    user = relationship("User")

