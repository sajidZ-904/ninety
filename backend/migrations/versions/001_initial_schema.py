"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # companies
    op.create_table(
        'companies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('timezone', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # users
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'team_member', 'observer')", name='check_user_role'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # teams
    op.create_table(
        'teams',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # memberships
    op.create_table(
        'memberships',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'team_id')
    )

    # measurables
    op.create_table(
        'measurables',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('unit', sa.String(), nullable=False),
        sa.Column('goal', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # scores
    op.create_table(
        'scores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('measurable_id', sa.String(), nullable=False),
        sa.Column('week_start', sa.String(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['measurable_id'], ['measurables.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('measurable_id', 'week_start', name='uq_measurable_week')
    )

    # rocks
    op.create_table(
        'rocks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('quarter', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.CheckConstraint("status IN ('on_track', 'off_track', 'complete')", name='check_rock_status'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # milestones
    op.create_table(
        'milestones',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('rock_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('due_date', sa.String(), nullable=False),
        sa.Column('done', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['rock_id'], ['rocks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # issues
    op.create_table(
        'issues',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('solved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('source_measurable_id', sa.String(), nullable=True),
        sa.Column('source_week_start', sa.String(), nullable=True),
        sa.CheckConstraint('priority IS NULL OR (priority >= 1 AND priority <= 5)', name='check_issue_priority'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.ForeignKeyConstraint(['source_measurable_id'], ['measurables.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'uq_unsolved_measurable_issue',
        'issues',
        ['source_measurable_id', 'source_week_start'],
        unique=True,
        postgresql_where=sa.text('solved_at IS NULL'),
        sqlite_where=sa.text('solved_at IS NULL')
    )

    # todos
    op.create_table(
        'todos',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('due_date', sa.String(), nullable=False),
        sa.Column('done_at', sa.DateTime(), nullable=True),
        sa.Column('source_issue_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.ForeignKeyConstraint(['source_issue_id'], ['issues.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # meetings
    op.create_table(
        'meetings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=False),
        sa.Column('facilitator_id', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('current_section', sa.String(), nullable=False),
        sa.Column('section_started_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['facilitator_id'], ['users.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'uq_active_meeting_per_team',
        'meetings',
        ['team_id'],
        unique=True,
        postgresql_where=sa.text('ended_at IS NULL'),
        sqlite_where=sa.text('ended_at IS NULL')
    )

    # meeting_attendees
    op.create_table(
        'meeting_attendees',
        sa.Column('meeting_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('meeting_id', 'user_id')
    )

    # meeting_ratings
    op.create_table(
        'meeting_ratings',
        sa.Column('meeting_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.CheckConstraint('rating >= 1 AND rating <= 10', name='check_meeting_rating'),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('meeting_id', 'user_id')
    )

def downgrade() -> None:
    op.drop_table('meeting_ratings')
    op.drop_table('meeting_attendees')
    op.drop_table('meetings')
    op.drop_table('todos')
    op.drop_index('uq_unsolved_measurable_issue', table_name='issues')
    op.drop_table('issues')
    op.drop_table('milestones')
    op.drop_table('rocks')
    op.drop_table('scores')
    op.drop_table('measurables')
    op.drop_table('memberships')
    op.drop_table('teams')
    op.drop_table('users')
    op.drop_table('companies')

