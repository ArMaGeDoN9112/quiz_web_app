from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260706_1700"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_ROLE = sa.Enum(
    "participant",
    "organizer",
    name="user_role",
    native_enum=False,
    create_constraint=True,
)

UPGRADE_OPERATIONS = [
    (
        "create_table",
        "users",
        [
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("role", USER_ROLE, nullable=False),
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
            sa.PrimaryKeyConstraint("id", name="pk_users"),
            sa.UniqueConstraint("email", name="uq_users_email"),
        ],
    )
]


def upgrade() -> None:
    for operation, table_name, columns, constraints in UPGRADE_OPERATIONS:
        if operation == "create_table":
            op.create_table(table_name, *columns, *constraints)


def downgrade() -> None:
    op.drop_table("users")
