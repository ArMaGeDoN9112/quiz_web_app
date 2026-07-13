from collections.abc import Collection, Sequence
from dataclasses import dataclass
from uuid import UUID


def score_selected_answers(
    *,
    selected_answer_ids: Collection[UUID],
    correct_answer_ids: Collection[UUID],
    question_points: int,
) -> int:
    """Return standard all-or-nothing points for a choice question."""
    if set(selected_answer_ids) == set(correct_answer_ids):
        return question_points
    return 0


@dataclass(frozen=True)
class ScoreCandidate:
    participant_id: UUID
    display_name: str
    joined_order: int
    score: int


@dataclass(frozen=True)
class RankedScore:
    participant_id: UUID
    display_name: str
    score: int
    rank: int


def rank_scoreboard(candidates: Sequence[ScoreCandidate]) -> tuple[list[RankedScore], list[UUID]]:
    ordered = sorted(candidates, key=lambda candidate: (-candidate.score, candidate.joined_order))
    entries: list[RankedScore] = []
    previous_score: int | None = None
    rank = 0
    for index, candidate in enumerate(ordered, start=1):
        if candidate.score != previous_score:
            rank = index
            previous_score = candidate.score
        entries.append(
            RankedScore(
                participant_id=candidate.participant_id,
                display_name=candidate.display_name,
                score=candidate.score,
                rank=rank,
            )
        )

    winner_ids = [entry.participant_id for entry in entries if entry.rank == 1]
    return entries, winner_ids
