import uuid
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.app.database import get_db, SessionLocal
from backend.app.models import (
    Meeting, MeetingAttendee, MeetingRating, User, Team,
    Measurable, Issue, ToDo, Membership
)
from backend.app.schemas import (
    MeetingStateOut, MeetingSummaryOut, MeetingRateRequest,
    MeetingRatingOut, ToDoOut, IssueOut, IssueSource
)
from backend.app.auth import (
    require_team_read, require_team_write, require_team_facilitator, get_current_user
)
from backend.app.clock import (
    get_app_now, get_last_closed_week, get_company_tz, get_today_local, as_utc,
    get_real_now_naive
)
from backend.app.rules import (
    compute_measurable_status, compute_meeting_rating, is_todo_overdue
)
from backend.app.socket_manager import manager

router = APIRouter(prefix="/api", tags=["Meetings"])

SECTION_DURATIONS = {
    "scorecard": 5 * 60, # 5 min = 300s
    "ids": 60 * 60,      # 60 min = 3600s
    "conclude": 10 * 60  # 10 min = 600s
}

NEXT_SECTIONS = {
    "scorecard": "ids",
    "ids": "conclude",
    "conclude": "ended"
}

def serialize_meeting_state(meeting: Meeting, db: Session) -> MeetingStateOut:
    now = get_app_now()
    section = meeting.current_section

    # Timer calculation: APP_NOW is pinned to the seed instant, so the live
    # section clock runs off the real wall-time anchor instead.
    elapsed = 0
    is_overtime = False
    if meeting.ended_at is None:
        sec_real = meeting.section_started_real_at or meeting.section_started_at
        if sec_real.tzinfo is None:
            sec_real = sec_real.replace(tzinfo=ZoneInfo("UTC"))
        elapsed = max(0, int((datetime.now(ZoneInfo("UTC")) - sec_real).total_seconds()))
    allocated = SECTION_DURATIONS.get(section, 0)
    if meeting.ended_at is None and elapsed > allocated:
        is_overtime = True

    attendees = [a.user_id for a in meeting.attendees]
    ratings = [
        MeetingRatingOut(user_id=r.user_id, rating=r.rating)
        for r in meeting.ratings
    ]

    # Scorecard week reviewed by this meeting (last closed week relative to meeting start)
    st = meeting.started_at
    if st.tzinfo is None:
        st = st.replace(tzinfo=ZoneInfo("UTC"))
    scorecard_w = get_last_closed_week(st)

    # Solved issues during meeting
    st_cmp = meeting.started_at.replace(tzinfo=None)
    end_cmp = meeting.ended_at.replace(tzinfo=None) if meeting.ended_at else now.replace(tzinfo=None)
    
    solved_q = db.query(Issue).filter(
        Issue.team_id == meeting.team_id,
        Issue.solved_at >= st_cmp,
        Issue.solved_at <= end_cmp
    ).all()

    # Todos created during meeting
    todos_q = db.query(ToDo).filter(
        ToDo.team_id == meeting.team_id,
        ToDo.created_at >= st_cmp,
        ToDo.created_at <= end_cmp
    ).all()

    today = get_today_local()
    new_todos = [
        ToDoOut(
            id=t.id,
            team_id=t.team_id,
            title=t.title,
            owner_id=t.owner_id,
            owner_name=t.owner.name if t.owner else None,
            due_date=t.due_date,
            done_at=as_utc(t.done_at) if t.done_at else None,
            source_issue_id=t.source_issue_id,
            created_at=as_utc(t.created_at),
            is_overdue=is_todo_overdue(t.due_date, t.done_at, today)
        )
        for t in todos_q
    ]

    solved_issues = [
        IssueOut(
            id=i.id,
            team_id=i.team_id,
            title=i.title,
            owner_id=i.owner_id,
            owner_name=i.owner.name if i.owner else None,
            priority=i.priority,
            created_at=as_utc(i.created_at),
            solved_at=as_utc(i.solved_at) if i.solved_at else None,
            resolution_note=i.resolution_note,
            source=IssueSource(measurable_id=i.source_measurable_id, week_start=i.source_week_start) if i.source_measurable_id else None
        )
        for i in solved_q
    ]

    return MeetingStateOut(
        id=meeting.id,
        team_id=meeting.team_id,
        facilitator_id=meeting.facilitator_id,
        facilitator_name=meeting.facilitator.name if meeting.facilitator else None,
        status="ended" if meeting.ended_at else "active",
        current_section=meeting.current_section,
        section_started_at=as_utc(meeting.section_started_at),
        started_at=as_utc(meeting.started_at),
        ended_at=as_utc(meeting.ended_at) if meeting.ended_at else None,
        server_now=as_utc(now),
        section_elapsed_seconds=elapsed,
        section_allocated_seconds=allocated,
        is_overtime=is_overtime,
        attendees=attendees,
        ratings=ratings,
        new_todos=new_todos,
        solved_issues=solved_issues,
        scorecard_week=scorecard_w
    )

@router.post("/teams/{team_id}/meetings/start", response_model=MeetingStateOut)
async def start_meeting(
    team_id: str,
    current_user: User = Depends(require_team_facilitator),
    db: Session = Depends(get_db)
):
    """
    Starts the Level 10 Meeting and becomes facilitator.
    One active meeting per team.
    """
    # Check active meeting
    active = db.query(Meeting).filter(
        Meeting.team_id == team_id,
        Meeting.ended_at.is_(None)
    ).first()
    if active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A meeting is already active for this team"
        )

    now = get_app_now()
    meeting_id = f"mt_{uuid.uuid4().hex[:8]}"

    meeting = Meeting(
        id=meeting_id,
        team_id=team_id,
        facilitator_id=current_user.id,
        started_at=now,
        ended_at=None,
        current_section="scorecard",
        section_started_at=now,
        section_started_real_at=get_real_now_naive()
    )
    db.add(meeting)
    try:
        db.flush()
        # Facilitator is the first attendee
        db.add(MeetingAttendee(meeting_id=meeting.id, user_id=current_user.id))
        db.commit()
    except IntegrityError:
        # Two facilitators started at the same moment; the partial unique
        # index on (team_id) WHERE ended_at IS NULL keeps exactly one.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A meeting was just started for this team"
        )
    db.refresh(meeting)

    state = serialize_meeting_state(meeting, db)
    await manager.broadcast(team_id, {
        "type": "meeting_started",
        "meeting": state.model_dump(mode="json")
    })

    return state

@router.get("/teams/{team_id}/meetings/current", response_model=MeetingStateOut | None)
def get_current_meeting(
    team_id: str,
    current_user: User = Depends(require_team_read),
    db: Session = Depends(get_db)
):
    """Returns currently active meeting for team, or null."""
    meeting = db.query(Meeting).filter(
        Meeting.team_id == team_id,
        Meeting.ended_at.is_(None)
    ).first()
    if not meeting:
        return None
    return serialize_meeting_state(meeting, db)

@router.get("/teams/{team_id}/meetings/latest-ended", response_model=MeetingStateOut | None)
def get_latest_ended_meeting(
    team_id: str,
    current_user: User = Depends(require_team_read),
    db: Session = Depends(get_db)
):
    """Ended meeting snapshot so refreshes and late viewers still see the summary."""
    meeting = (
        db.query(Meeting)
        .filter(Meeting.team_id == team_id, Meeting.ended_at.isnot(None))
        .order_by(Meeting.ended_at.desc())
        .first()
    )
    if not meeting:
        return None
    return serialize_meeting_state(meeting, db)

@router.post("/meetings/{meeting_id}/join", response_model=MeetingStateOut)
async def join_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Anyone who can read the team can join."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    require_team_read(meeting.team_id, current_user, db)

    if meeting.ended_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting has ended")

    existing = db.query(MeetingAttendee).filter(
        MeetingAttendee.meeting_id == meeting.id,
        MeetingAttendee.user_id == current_user.id
    ).first()
    if not existing:
        db.add(MeetingAttendee(meeting_id=meeting.id, user_id=current_user.id))
        db.commit()
        db.refresh(meeting)

    state = serialize_meeting_state(meeting, db)
    await manager.broadcast(meeting.team_id, {
        "type": "meeting_updated",
        "meeting": state.model_dump(mode="json")
    })

    return state

@router.post("/meetings/{meeting_id}/advance", response_model=MeetingStateOut)
async def advance_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Only the facilitator advances the section."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if meeting.ended_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting has ended")

    if meeting.facilitator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only facilitator can advance section")

    next_sec = NEXT_SECTIONS.get(meeting.current_section)
    if not next_sec or next_sec == "ended":
        # Conclude -> end meeting
        now = get_app_now()
        meeting.ended_at = now
        meeting.current_section = "ended"
    else:
        now = get_app_now()
        meeting.current_section = next_sec
        meeting.section_started_at = now
        meeting.section_started_real_at = get_real_now_naive()

    db.commit()
    db.refresh(meeting)

    state = serialize_meeting_state(meeting, db)
    await manager.broadcast(meeting.team_id, {
        "type": "meeting_updated",
        "meeting": state.model_dump(mode="json")
    })

    return state

@router.post("/meetings/{meeting_id}/rate")
async def rate_meeting(
    meeting_id: str,
    payload: MeetingRateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    In Conclude, each attending Admin or Team Member rates 1 to 10 and can change it until the end.
    Observers cannot rate.
    """
    if current_user.role == "observer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Observers cannot rate meetings")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if meeting.ended_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting has already ended")

    require_team_read(meeting.team_id, current_user, db)

    if meeting.current_section != "conclude":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ratings are only accepted in Conclude")

    # Verify user is an attendee
    att = db.query(MeetingAttendee).filter(
        MeetingAttendee.meeting_id == meeting.id,
        MeetingAttendee.user_id == current_user.id
    ).first()
    if not att:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only attendees can rate this meeting")

    rating_record = db.query(MeetingRating).filter(
        MeetingRating.meeting_id == meeting.id,
        MeetingRating.user_id == current_user.id
    ).first()

    if not rating_record:
        rating_record = MeetingRating(
            meeting_id=meeting.id,
            user_id=current_user.id,
            rating=payload.rating
        )
        db.add(rating_record)
    else:
        rating_record.rating = payload.rating

    db.commit()
    db.refresh(meeting)

    state = serialize_meeting_state(meeting, db)
    await manager.broadcast(meeting.team_id, {
        "type": "meeting_updated",
        "meeting": state.model_dump(mode="json")
    })

    return {"status": "ok", "rating": payload.rating}

@router.post("/meetings/{meeting_id}/end", response_model=MeetingStateOut)
async def end_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Facilitator ends meeting at any time."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    if meeting.facilitator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only facilitator can end meeting")

    if meeting.ended_at is None:
        now = get_app_now()
        meeting.ended_at = now
        meeting.current_section = "ended"
        db.commit()
        db.refresh(meeting)

    state = serialize_meeting_state(meeting, db)
    await manager.broadcast(meeting.team_id, {
        "type": "meeting_ended",
        "meeting": state.model_dump(mode="json")
    })

    return state

@router.get("/meetings/{meeting_id}/summary", response_model=MeetingSummaryOut)
def get_meeting_summary(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns summary for any ended meeting, including the 2 seeded ones (mt1, mt2).
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    require_team_read(meeting.team_id, current_user, db)

    # Scorecard week is the week reviewed (last closed week when meeting started)
    st = meeting.started_at
    if st.tzinfo is None:
        st = st.replace(tzinfo=ZoneInfo("UTC"))
    sc_week = get_last_closed_week(st)

    # Measurable status for scorecard_week
    measurables = db.query(Measurable).filter(Measurable.team_id == meeting.team_id).order_by(Measurable.id).all()
    m_statuses = {}
    for m in measurables:
        score = [s for s in m.scores if s.week_start == sc_week]
        val = score[0].value if score else None
        m_statuses[m.id] = compute_measurable_status(m.goal, val, sc_week, sc_week, closed_week=True)

    # Issues solved during meeting
    st_cmp = meeting.started_at.replace(tzinfo=None)
    end_cmp = meeting.ended_at.replace(tzinfo=None) if meeting.ended_at else get_app_now().replace(tzinfo=None)
    solved = db.query(Issue).filter(
        Issue.team_id == meeting.team_id,
        Issue.solved_at >= st_cmp,
        Issue.solved_at <= end_cmp
    ).all()
    solved_ids = sorted([i.id for i in solved])

    # To-Dos created during meeting
    todos = db.query(ToDo).filter(
        ToDo.team_id == meeting.team_id,
        ToDo.created_at >= st_cmp,
        ToDo.created_at <= end_cmp
    ).all()
    todo_ids = sorted([t.id for t in todos])

    # Attendees
    attendee_ids = sorted([a.user_id for a in meeting.attendees])

    # Rating
    ratings = [r.rating for r in meeting.ratings]
    avg_rating = compute_meeting_rating(ratings)

    return MeetingSummaryOut(
        meeting_id=meeting.id,
        team_id=meeting.team_id,
        scorecard_week=sc_week,
        measurable_status=m_statuses,
        issues_solved=solved_ids,
        todos_created=todo_ids,
        attendee_ids=attendee_ids,
        rating=avg_rating
    )

@router.websocket("/meetings/{team_id}/ws")
async def meeting_websocket(websocket: WebSocket, team_id: str, user_id: str = Query(...)):
    """WebSocket endpoint for real-time meeting state and presence.

    The connection is authenticated with the same x-user-id identity the REST
    API uses (passed as a query parameter because browsers cannot set headers
    on WebSocket handshakes) and enforces the team read boundary.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        allowed = user is not None and (
            user.role == "admin"
            or db.query(Membership).filter(
                Membership.user_id == user.id, Membership.team_id == team_id
            ).first() is not None
        )
    finally:
        db.close()

    if not allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(team_id, websocket)
    try:
        while True:
            # Keep socket alive and receive heartbeat / ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(team_id, websocket)
    except Exception:
        manager.disconnect(team_id, websocket)

