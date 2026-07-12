from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260706_1800"
down_revision: str | Sequence[str] | None = "20260706_1700"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

QUIZ_STATUS = sa.Enum(
    "draft",
    "published",
    "archived",
    name="quiz_status",
    native_enum=False,
    create_constraint=True,
)
QUESTION_TYPE = sa.Enum(
    "text",
    "image",
    name="question_type",
    native_enum=False,
    create_constraint=True,
)
CHOICE_MODE = sa.Enum(
    "single",
    "multiple",
    name="choice_mode",
    native_enum=False,
    create_constraint=True,
)

UPGRADE_OPERATIONS = [
    (
        "create_table",
        "categories",
        [
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
        ],
        [
            sa.PrimaryKeyConstraint("id", name="pk_categories"),
            sa.UniqueConstraint("name", name="uq_categories_name"),
        ],
    ),
    (
        "create_table",
        "quizzes",
        [
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", QUIZ_STATUS, server_default="draft", nullable=False),
            sa.Column(
                "settings",
                sa.JSON(),
                server_default=sa.text("'{}'::json"),
                nullable=False,
            ),
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
        ],
        [
            sa.PrimaryKeyConstraint("id", name="pk_quizzes"),
            sa.ForeignKeyConstraint(
                ["owner_id"],
                ["users.id"],
                name="fk_quizzes_owner_id_users",
                ondelete="CASCADE",
            ),
        ],
    ),
    (
        "create_table",
        "questions",
        [
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("quiz_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("type", QUESTION_TYPE, nullable=False),
            sa.Column("choice_mode", CHOICE_MODE, nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("image_url", sa.String(length=2048), nullable=True),
            sa.Column("points", sa.Integer(), server_default="1", nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
        ],
        [
            sa.PrimaryKeyConstraint("id", name="pk_questions"),
            sa.ForeignKeyConstraint(
                ["quiz_id"],
                ["quizzes.id"],
                name="fk_questions_quiz_id_quizzes",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["category_id"],
                ["categories.id"],
                name="fk_questions_category_id_categories",
                ondelete="SET NULL",
            ),
        ],
    ),
    (
        "create_table",
        "answers",
        [
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("is_correct", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
        ],
        [
            sa.PrimaryKeyConstraint("id", name="pk_answers"),
            sa.ForeignKeyConstraint(
                ["question_id"],
                ["questions.id"],
                name="fk_answers_question_id_questions",
                ondelete="CASCADE",
            ),
        ],
    ),
]


def upgrade() -> None:
    for operation, table_name, columns, constraints in UPGRADE_OPERATIONS:
        if operation == "create_table":
            op.create_table(table_name, *columns, *constraints)


def downgrade() -> None:
    op.drop_table("answers")
    op.drop_table("questions")
    op.drop_table("quizzes")
    op.drop_table("categories")
