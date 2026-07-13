from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260713_0300"
down_revision: str | Sequence[str] | None = "20260713_0200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="30"),
    )


def downgrade() -> None:
    op.drop_column("questions", "duration_seconds")
