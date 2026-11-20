"""meeting live timer anchor

Revision ID: 002_meeting_real_timer
Revises: 001_initial_schema
Create Date: 2026-11-20 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_meeting_real_timer'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('meetings', sa.Column('section_started_real_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('meetings', 'section_started_real_at')
