from uuid import uuid4

from app.services.scoring import ScoreCandidate, rank_scoreboard, score_selected_answers


def test_score_single_choice_awards_question_points_only_for_correct_answer() -> None:
    correct_answer_id = uuid4()

    assert score_selected_answers(
        selected_answer_ids=[correct_answer_id],
        correct_answer_ids={correct_answer_id},
        question_points=7,
    ) == 7
    assert score_selected_answers(
        selected_answer_ids=[uuid4()],
        correct_answer_ids={correct_answer_id},
        question_points=7,
    ) == 0


def test_score_multiple_choice_requires_exact_correct_selection() -> None:
    first_correct_answer_id = uuid4()
    second_correct_answer_id = uuid4()

    assert score_selected_answers(
        selected_answer_ids=[first_correct_answer_id, second_correct_answer_id],
        correct_answer_ids={first_correct_answer_id, second_correct_answer_id},
        question_points=10,
    ) == 10
    assert score_selected_answers(
        selected_answer_ids=[first_correct_answer_id],
        correct_answer_ids={first_correct_answer_id, second_correct_answer_id},
        question_points=10,
    ) == 0


def test_rank_scoreboard_assigns_shared_rank_and_all_winners() -> None:
    first = uuid4()
    second = uuid4()
    third = uuid4()

    entries, winner_ids = rank_scoreboard(
        [
            ScoreCandidate(participant_id=third, display_name="Cleo", joined_order=3, score=4),
            ScoreCandidate(participant_id=second, display_name="Bert", joined_order=2, score=9),
            ScoreCandidate(participant_id=first, display_name="Ada", joined_order=1, score=9),
        ]
    )

    assert [(entry.participant_id, entry.rank, entry.score) for entry in entries] == [
        (first, 1, 9),
        (second, 1, 9),
        (third, 3, 4),
    ]
    assert winner_ids == [first, second]
