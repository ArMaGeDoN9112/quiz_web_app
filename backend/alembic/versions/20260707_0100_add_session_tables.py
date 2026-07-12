from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260707_0100"
down_revision: str | Sequence[str] | None = "20260707_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SESSION_STATUS = sa.Enum(
    "waiting",
    "active",
    "ended",
    name="session_status",
    native_enum=False,
    create_constraint=True,
)
QUESTION_EVENT_STATUS = sa.Enum(
    "scheduled",
    "active",
    "closed",
    name="question_event_status",
    native_enum=False,
    create_constraint=True,
)

UPGRADE_OPERATIONS = [
    (
        "create_table",
        "sessions",
        [
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("quiz_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organizer_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("room_code", sa.String(length=16), nullable=False),
            sa.Column("status", SESSION_STATUS, server_default="waiting", nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        ],
        [
            sa.PrimaryKeyConstraint("id", name="pk_sessions"),
            sa.ForeignKeyConstraint(
                ["quiz_id"],
                ["quizzes.id"],
                name="fk_sessions_quiz_id_quizzes",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["organizer_id"],
                ["users.id"],
                name="fk_sessions_organizer_id_users",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("room_code", name="uq_sessions_room_code"),
        ],
    ),
    (
        "create_table",
        "session_participants",
        [
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("display_name", sa.String(length=100), nullable=False),
            sa.Column(
                "joined_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        ],
        [
            sa.PrimaryKeyConstraint("id", name="pk_session_participants"),
            sa.ForeignKeyConstraint(
                ["session_id"],
                ["sessions.id"],
                name="fk_session_participants_session_id_sessions",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_session_participants_user_id_users",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "session_id",
                "user_id",
                name="uq_session_participants_session_id_user_id",
            ),
        ],
    ),
    (
        "create_table",
        "question_events",
        [
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "status",
                QUESTION_EVENT_STATUS,
                server_default="scheduled",
                nullable=False,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        ],
        [
            sa.PrimaryKeyConstraint("id", name="pk_question_events"),
            sa.ForeignKeyConstraint(
                ["session_id"],
                ["sessions.id"],
                name="fk_question_events_session_id_sessions",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["question_id"],
                ["questions.id"],
                name="fk_question_events_question_id_questions",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "session_id",
                "question_id",
                name="uq_question_events_session_id_question_id",
            ),
        ],
    ),
    (
        "create_table",
        "question_responses",
        [
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("question_event_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("selected_answer_ids", sa.JSON(), nullable=False),
            sa.Column("text_answer", sa.String(length=2000), nullable=True),
            sa.Column(
                "submitted_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("meta", sa.JSON(), nullable=False),
        ],
        [
            sa.PrimaryKeyConstraint("id", name="pk_question_responses"),
            sa.ForeignKeyConstraint(
                ["participant_id"],
                ["session_participants.id"],
                name="fk_question_responses_participant_id_session_participants",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["question_event_id"],
                ["question_events.id"],
                name="fk_question_responses_question_event_id_question_events",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "participant_id",
                "question_event_id",
                name="uq_question_responses_participant_id_question_event_id",
            ),
        ],
    ),
]


def upgrade() -> None:
    for operation, table_name, columns, constraints in UPGRADE_OPERATIONS:
        if operation == "create_table":
            op.create_table(table_name, *columns, *constraints)


def downgrade() -> None:
    op.drop_table("question_responses")
    op.drop_table("question_events")
    op.drop_table("session_participants")
    op.drop_table("sessions")
