import importlib.util
from pathlib import Path


def _load_migration_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260713_0300_add_quiz_playback_duration.py"
    )
    spec = importlib.util.spec_from_file_location("playback_migration", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_playback_migration_adds_question_duration(monkeypatch) -> None:
    migration = _load_migration_module()
    added_columns: list[tuple[str, object]] = []

    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table, column: added_columns.append((table, column)),
    )

    migration.upgrade()

    assert migration.revision == "20260713_0300"
    assert migration.down_revision == "20260713_0200"
    assert added_columns[0][0] == "questions"
    assert added_columns[0][1].name == "duration_seconds"
    assert added_columns[0][1].nullable is False
