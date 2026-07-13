from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260713_0100"
down_revision: str | Sequence[str] | None = "20260707_0200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "question_responses",
        sa.Column("awarded_points", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("sessions", sa.Column("final_results", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "final_results")
    op.drop_column("question_responses", "awarded_points")
