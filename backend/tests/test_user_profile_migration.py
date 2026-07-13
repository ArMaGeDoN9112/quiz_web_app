import importlib.util
from pathlib import Path


def _load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260713_0200_add_user_display_name.py"
    )
    spec = importlib.util.spec_from_file_location("user_profile_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_user_profile_migration_adds_nullable_display_name(monkeypatch) -> None:
    migration = _load_migration_module()
    added_columns: list[tuple[str, object]] = []

    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table_name, column: added_columns.append((table_name, column)),
    )

    migration.upgrade()

    assert migration.revision == "20260713_0200"
    assert migration.down_revision == "20260713_0100"
    assert added_columns[0][0] == "users"
    assert added_columns[0][1].name == "display_name"
    assert added_columns[0][1].nullable is True
