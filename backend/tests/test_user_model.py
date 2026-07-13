from sqlalchemy import UniqueConstraint

from app.db.base import Base
from app.models import User, UserRole


def test_user_model_matches_auth_database_contract() -> None:
    table = User.__table__

    assert table.name == "users"
    assert table in Base.metadata.tables.values()
    assert set(table.c.keys()) == {
        "id",
        "email",
        "display_name",
        "password_hash",
        "role",
        "created_at",
        "updated_at",
    }
    assert table.c.email.nullable is False
    assert table.c.display_name.nullable is True
    assert table.c.password_hash.nullable is False
    assert table.c.role.nullable is False


def test_user_role_is_constrained_to_public_role_values() -> None:
    assert [role.value for role in UserRole] == ["participant", "organizer"]
    assert User.__table__.c.role.type.enums == ["participant", "organizer"]


def test_user_email_has_unique_constraint() -> None:
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in User.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("email",) in unique_columns
