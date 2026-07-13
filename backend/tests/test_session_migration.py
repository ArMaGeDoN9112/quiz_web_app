import importlib.util
from pathlib import Path


def _load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260707_0100_add_session_tables.py"
    )
    spec = importlib.util.spec_from_file_location("session_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_active_event_index_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260707_0200_add_active_question_event_unique_index.py"
    )
    spec = importlib.util.spec_from_file_location(
        "active_question_event_index_migration", migration_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_scoring_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260713_0100_add_question_response_awarded_points.py"
    )
    spec = importlib.util.spec_from_file_location("scoring_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_session_migration_extends_question_position_revision() -> None:
    migration = _load_migration_module()

    assert migration.revision == "20260707_0100"
    assert migration.down_revision == "20260707_0001"


def test_session_migration_creates_session_tables() -> None:
    migration = _load_migration_module()

    create_table_names = [
        operation[1]
        for operation in migration.UPGRADE_OPERATIONS
        if operation[0] == "create_table"
    ]

    assert create_table_names == [
        "sessions",
        "session_participants",
        "question_events",
        "question_responses",
    ]


def test_session_migration_declares_expected_uniques() -> None:
    migration = _load_migration_module()
    constraints_by_table = {
        table_name: constraints
        for operation, table_name, _, constraints in migration.UPGRADE_OPERATIONS
        if operation == "create_table"
    }

    assert any(
        constraint.name == "uq_sessions_room_code"
        for constraint in constraints_by_table["sessions"]
    )
    assert any(
        constraint.name == "uq_session_participants_session_id_user_id"
        for constraint in constraints_by_table["session_participants"]
    )
    assert any(
        constraint.name == "uq_question_events_session_id_question_id"
        for constraint in constraints_by_table["question_events"]
    )
    assert any(
        constraint.name == "uq_question_responses_participant_id_question_event_id"
        for constraint in constraints_by_table["question_responses"]
    )


def test_session_migration_declares_expected_foreign_keys() -> None:
    migration = _load_migration_module()
    constraints_by_table = {
        table_name: constraints
        for operation, table_name, _, constraints in migration.UPGRADE_OPERATIONS
        if operation == "create_table"
    }

    assert any(
        constraint.name == "fk_sessions_quiz_id_quizzes"
        for constraint in constraints_by_table["sessions"]
    )
    assert any(
        constraint.name == "fk_sessions_organizer_id_users"
        for constraint in constraints_by_table["sessions"]
    )
    assert any(
        constraint.name == "fk_session_participants_session_id_sessions"
        for constraint in constraints_by_table["session_participants"]
    )
    assert any(
        constraint.name == "fk_session_participants_user_id_users"
        for constraint in constraints_by_table["session_participants"]
    )
    assert any(
        constraint.name == "fk_question_events_session_id_sessions"
        for constraint in constraints_by_table["question_events"]
    )
    assert any(
        constraint.name == "fk_question_events_question_id_questions"
        for constraint in constraints_by_table["question_events"]
    )
    assert any(
        constraint.name == "fk_question_responses_participant_id_session_participants"
        for constraint in constraints_by_table["question_responses"]
    )
    assert any(
        constraint.name == "fk_question_responses_question_event_id_question_events"
        for constraint in constraints_by_table["question_responses"]
    )


def test_active_question_event_index_migration_adds_partial_unique_index() -> None:
    migration = _load_active_event_index_migration_module()

    assert migration.revision == "20260707_0200"
    assert migration.down_revision == "20260707_0100"
    assert migration.INDEX_NAME == "uq_question_events_active_session_id"
    assert migration.TABLE_NAME == "question_events"
    assert migration.COLUMNS == ["session_id"]
    assert "status = 'active'" in str(migration.POSTGRESQL_WHERE)


def test_scoring_migration_adds_response_points_and_final_results(monkeypatch) -> None:
    migration = _load_scoring_migration_module()
    added_columns = []

    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table_name, column: added_columns.append((table_name, column.name)),
    )

    migration.upgrade()

    assert migration.revision == "20260713_0100"
    assert migration.down_revision == "20260707_0200"
    assert added_columns == [
        ("question_responses", "awarded_points"),
        ("sessions", "final_results"),
    ]
