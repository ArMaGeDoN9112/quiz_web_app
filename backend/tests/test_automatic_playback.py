from uuid import uuid4

from app.models import ChoiceMode, Question, QuestionType
from app.services.playback import select_next_automatic_question


def _question(position: int) -> Question:
    question = Question(
        quiz_id=uuid4(),
        type=QuestionType.TEXT,
        choice_mode=ChoiceMode.SINGLE,
        text=f"Question {position}",
        points=1,
        duration_seconds=30,
        position=position,
    )
    question.id = uuid4()
    return question


def test_automatic_playback_selects_lowest_unused_position() -> None:
    first, second, third = (_question(position) for position in (1, 2, 3))

    next_question = select_next_automatic_question(
        [third, first, second],
        used_question_ids={first.id},
        shuffle_questions=False,
    )

    assert next_question is second


def test_automatic_playback_uses_server_randomizer_for_shuffled_quiz() -> None:
    first, second, third = (_question(position) for position in (1, 2, 3))

    next_question = select_next_automatic_question(
        [first, second, third],
        used_question_ids={first.id},
        shuffle_questions=True,
        choice=lambda questions: questions[-1],
    )

    assert next_question is third


def test_automatic_playback_returns_none_when_every_question_was_used() -> None:
    first, second = (_question(position) for position in (1, 2))

    assert select_next_automatic_question(
        [first, second],
        used_question_ids={first.id, second.id},
        shuffle_questions=False,
    ) is None
