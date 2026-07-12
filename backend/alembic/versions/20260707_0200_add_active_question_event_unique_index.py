from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260707_0200"
down_revision: str | Sequence[str] | None = "20260707_0100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_question_events_active_session_id"
TABLE_NAME = "question_events"
COLUMNS = ["session_id"]
POSTGRESQL_WHERE = sa.text("status = 'active'")


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        TABLE_NAME,
        COLUMNS,
        unique=True,
        postgresql_where=POSTGRESQL_WHERE,
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
