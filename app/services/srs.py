from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


SMALL_DELAY_SECONDS = 45  # "after few cards" approximation


@dataclass(frozen=True)
class SrsResult:
    status: str           # new | learning | mastered
    stage: int | None     # 1..5 when learning
    due_at: datetime | None


def schedule_next(*, status: str, stage: int | None, learned: bool, now: datetime) -> SrsResult:
    """
    3 states:
      - new
      - learning (stage 1..5)
      - mastered

    5 learning stages:
      1: current section (soon)
      2: +5 minutes
      3: +1 hour
      4: +12 hours
      5: +72 hours  -> if passed, become MASTERED
    """
    # MASTERED stays mastered (for now)
    if status == "mastered":
        return SrsResult(status="mastered", stage=stage, due_at=None)

    # NEW state rules
    if status == "new":
        if not learned:
            # still new, see again soon
            return SrsResult(status="new", stage=None, due_at=now + timedelta(seconds=SMALL_DELAY_SECONDS))

        # learned == True: enter ladder
        return SrsResult(status="learning", stage=1, due_at=now + timedelta(seconds=SMALL_DELAY_SECONDS))

    # LEARNING rules
    if status == "learning":
        cur_stage = int(stage or 1)

        if not learned:
            # softer: drop only 1 stage (min 1), repeat soon
            new_stage = max(1, cur_stage - 1)
            return SrsResult(
                status="learning",
                stage=new_stage,
                due_at=now + timedelta(seconds=SMALL_DELAY_SECONDS),
            )

        # learned == True: move forward
        if cur_stage == 1:
            return SrsResult(status="learning", stage=2, due_at=now + timedelta(minutes=5))
        if cur_stage == 2:
            return SrsResult(status="learning", stage=3, due_at=now + timedelta(hours=1))
        if cur_stage == 3:
            return SrsResult(status="learning", stage=4, due_at=now + timedelta(hours=12))
        if cur_stage == 4:
            return SrsResult(status="learning", stage=5, due_at=now + timedelta(hours=72))

        # cur_stage >= 5 and learned == True => MASTERED
        return SrsResult(status="mastered", stage=5, due_at=None)

    # fallback
    return SrsResult(status="new", stage=None, due_at=now + timedelta(seconds=SMALL_DELAY_SECONDS))