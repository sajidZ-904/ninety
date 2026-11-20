from datetime import datetime, date
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator

# User & Team
class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True

class TeamOut(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True

# Score & Measurable
class ScoreUpdate(BaseModel):
    value: float
    version: Optional[int] = None

class ScoreOut(BaseModel):
    measurable_id: str
    week_start: str
    value: float
    version: int

    class Config:
        from_attributes = True

class GoalSchema(BaseModel):
    type: str # at_least, at_most, between, exactly
    value: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None

class MeasurableWeekStatus(BaseModel):
    week_start: str
    value: Optional[float] = None
    status: str # on_track, off_track, pending
    version: Optional[int] = None

class MeasurableOut(BaseModel):
    id: str
    team_id: str
    name: str
    owner_id: str
    owner_name: Optional[str] = None
    unit: str
    goal: dict[str, Any]
    weeks: list[MeasurableWeekStatus]

# Issues
class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1)
    priority: Optional[int] = Field(None, ge=1, le=5)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title is required")
        return value

class MakeIssueRequest(BaseModel):
    measurable_id: str
    week_start: str

    @field_validator("week_start")
    @classmethod
    def week_start_is_monday(cls, value: str) -> str:
        if date.fromisoformat(value).weekday() != 0:
            raise ValueError("week_start must be a Monday")
        return value

class IssuePriorityUpdate(BaseModel):
    priority: Optional[int] = Field(None, ge=1, le=5)

class IssueSolveRequest(BaseModel):
    resolution_note: str = Field(..., min_length=1)

class IssueSource(BaseModel):
    measurable_id: str
    week_start: str

class IssueOut(BaseModel):
    id: str
    team_id: str
    title: str
    owner_id: str
    owner_name: Optional[str] = None
    priority: Optional[int] = None
    created_at: datetime
    solved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    source: Optional[IssueSource] = None

# To-Dos
class ToDoCreate(BaseModel):
    title: str = Field(..., min_length=1)
    owner_id: str
    due_date: Optional[str] = None # defaults to 7 days from today in company time
    source_issue_id: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title is required")
        return value

    @field_validator("due_date")
    @classmethod
    def due_date_is_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            date.fromisoformat(value)
        return value

class ToDoOut(BaseModel):
    id: str
    team_id: str
    title: str
    owner_id: str
    owner_name: Optional[str] = None
    due_date: str
    done_at: Optional[datetime] = None
    source_issue_id: Optional[str] = None
    created_at: datetime
    is_overdue: bool = False

# Rocks & Milestones
class MilestoneOut(BaseModel):
    id: str
    rock_id: str
    title: str
    due_date: str
    done: bool

    class Config:
        from_attributes = True

class RockOut(BaseModel):
    id: str
    team_id: str
    title: str
    owner_id: str
    owner_name: Optional[str] = None
    quarter: str
    status: str # on_track, off_track, complete (computed)
    progress_percent: int # 0 to 100
    milestones: list[MilestoneOut]

# Meetings
class MeetingStartRequest(BaseModel):
    pass

class MeetingAdvanceRequest(BaseModel):
    pass

class MeetingRateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=10)

class MeetingAttendeeOut(BaseModel):
    user_id: str
    name: str
    role: str

class MeetingRatingOut(BaseModel):
    user_id: str
    rating: int

class MeetingStateOut(BaseModel):
    id: str
    team_id: str
    facilitator_id: str
    facilitator_name: Optional[str] = None
    status: str # active, ended
    current_section: str # scorecard, ids, conclude, ended
    section_started_at: datetime
    started_at: datetime
    ended_at: Optional[datetime] = None
    server_now: datetime
    section_elapsed_seconds: int
    section_allocated_seconds: int
    is_overtime: bool
    attendees: list[str] # user IDs
    ratings: list[MeetingRatingOut]
    new_todos: list[ToDoOut]
    solved_issues: list[IssueOut]
    scorecard_week: str

class MeetingSummaryOut(BaseModel):
    meeting_id: str
    team_id: str
    scorecard_week: str
    measurable_status: dict[str, str]
    issues_solved: list[str] # IDs
    todos_created: list[str] # IDs
    attendee_ids: list[str] # IDs
    rating: Optional[float] = None

