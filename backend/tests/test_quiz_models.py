from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app.db.base import Base
from app.models import (
    Answer,
    Category,
    ChoiceMode,
    Question,
    QuestionType,
    Quiz,
    QuizStatus,
)


def test_quiz_models_are_registered_with_metadata() -> None:
    assert Quiz.__table__ in Base.metadata.tables.values()
    assert Category.__table__ in Base.metadata.tables.values()
    assert Question.__table__ in Base.metadata.tables.values()
    assert Answer.__table__ in Base.metadata.tables.values()


def test_quiz_table_matches_database_contract() -> None:
    table = Quiz.__table__

    assert table.name == "quizzes"
    assert set(table.c.keys()) == {
        "id",
        "owner_id",
        "title",
        "description",
        "status",
        "settings",
        "created_at",
        "updated_at",
    }
    assert table.c.owner_id.nullable is False
    assert table.c.title.nullable is False
    assert table.c.status.nullable is False
    assert table.c.settings.nullable is False
    assert QuizStatus.__members__.keys() == {"DRAFT", "PUBLISHED", "ARCHIVED"}
    assert table.c.status.type.enums == ["draft", "published", "archived"]


def test_category_table_has_unique_name() -> None:
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in Category.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert Category.__table__.name == "categories"
    assert set(Category.__table__.c.keys()) == {"id", "name"}
    assert ("name",) in unique_columns


def test_question_table_constrains_type_and_choice_mode() -> None:
    table = Question.__table__
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert table.name == "questions"
    assert set(table.c.keys()) == {
        "id",
        "quiz_id",
        "category_id",
        "type",
        "choice_mode",
        "text",
        "image_url",
        "points",
        "position",
    }
    assert QuestionType.__members__.keys() == {"TEXT", "IMAGE"}
    assert ChoiceMode.__members__.keys() == {"SINGLE", "MULTIPLE"}
    assert table.c.type.type.enums == ["text", "image"]
    assert table.c.choice_mode.type.enums == ["single", "multiple"]
    assert table.c.quiz_id.nullable is False
    assert table.c.category_id.nullable is True
    assert table.c.points.nullable is False
    assert table.c.position.nullable is False
    assert ("quiz_id", "position") in unique_columns


def test_answer_table_matches_database_contract() -> None:
    table = Answer.__table__

    assert table.name == "answers"
    assert set(table.c.keys()) == {
        "id",
        "question_id",
        "text",
        "is_correct",
        "position",
    }
    assert table.c.question_id.nullable is False
    assert table.c.text.nullable is False
    assert table.c.is_correct.nullable is False
    assert table.c.position.nullable is False


def test_quiz_models_have_expected_foreign_keys() -> None:
    foreign_keys = {
        (constraint.name, tuple(constraint.column_keys), constraint.elements[0].target_fullname)
        for table in (Quiz.__table__, Question.__table__, Answer.__table__)
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert (
        "fk_quizzes_owner_id_users",
        ("owner_id",),
        "users.id",
    ) in foreign_keys
    assert (
        "fk_questions_quiz_id_quizzes",
        ("quiz_id",),
        "quizzes.id",
    ) in foreign_keys
    assert (
        "fk_questions_category_id_categories",
        ("category_id",),
        "categories.id",
    ) in foreign_keys
    assert (
        "fk_answers_question_id_questions",
        ("question_id",),
        "questions.id",
    ) in foreign_keys
