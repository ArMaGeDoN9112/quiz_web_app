from collections.abc import Sequence

from alembic import op

revision: str = "20260707_0001"
down_revision: str | Sequence[str] | None = "20260706_1800"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "uq_questions_quiz_id_position"
TABLE_NAME = "questions"
COLUMNS = ["quiz_id", "position"]


def upgrade() -> None:
    op.create_unique_constraint(CONSTRAINT_NAME, TABLE_NAME, COLUMNS)


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, TABLE_NAME, type_="unique")
