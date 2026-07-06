import importlib.util
from pathlib import Path


def _load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260706_1700_add_users_table.py"
    )
    spec = importlib.util.spec_from_file_location("users_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_users_migration_declares_initial_revision() -> None:
    migration = _load_migration_module()

    assert migration.revision == "20260706_1700"
    assert migration.down_revision is None


def test_users_migration_creates_users_table_with_constraints() -> None:
    migration = _load_migration_module()

    create_table_call = next(
        operation for operation in migration.UPGRADE_OPERATIONS if operation[0] == "create_table"
    )
    table_name, columns, constraints = create_table_call[1:]

    assert table_name == "users"
    assert {column.name for column in columns} == {
        "id",
        "email",
        "password_hash",
        "role",
        "created_at",
        "updated_at",
    }
    assert any(constraint.name == "uq_users_email" for constraint in constraints)
    assert columns[3].type.enums == ["participant", "organizer"]
