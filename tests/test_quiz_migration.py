import importlib.util
from pathlib import Path


def _load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260706_1800_add_quiz_tables.py"
    )
    spec = importlib.util.spec_from_file_location("quiz_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quiz_migration_extends_user_revision() -> None:
    migration = _load_migration_module()

    assert migration.revision == "20260706_1800"
    assert migration.down_revision == "20260706_1700"


def test_quiz_migration_creates_quiz_tables() -> None:
    migration = _load_migration_module()

    create_table_names = [
        operation[1]
        for operation in migration.UPGRADE_OPERATIONS
        if operation[0] == "create_table"
    ]

    assert create_table_names == ["categories", "quizzes", "questions", "answers"]


def test_quiz_migration_constrains_question_enums() -> None:
    migration = _load_migration_module()

    questions_call = next(
        operation
        for operation in migration.UPGRADE_OPERATIONS
        if operation[0] == "create_table" and operation[1] == "questions"
    )
    _, _, columns, _ = questions_call
    columns_by_name = {column.name: column for column in columns}

    assert columns_by_name["type"].type.enums == ["text", "image"]
    assert columns_by_name["choice_mode"].type.enums == ["single", "multiple"]


def test_quiz_migration_declares_expected_foreign_keys() -> None:
    migration = _load_migration_module()

    constraints_by_table = {
        table_name: constraints
        for operation, table_name, _, constraints in migration.UPGRADE_OPERATIONS
        if operation == "create_table"
    }

    assert any(
        constraint.name == "fk_quizzes_owner_id_users"
        for constraint in constraints_by_table["quizzes"]
    )
    assert any(
        constraint.name == "fk_questions_quiz_id_quizzes"
        for constraint in constraints_by_table["questions"]
    )
    assert any(
        constraint.name == "fk_questions_category_id_categories"
        for constraint in constraints_by_table["questions"]
    )
    assert any(
        constraint.name == "fk_answers_question_id_questions"
        for constraint in constraints_by_table["answers"]
    )
