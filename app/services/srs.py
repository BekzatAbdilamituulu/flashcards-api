import random
from dataclasses import dataclass

@dataclass
class Sm2State:
    ease_factor: float
    interval_days: int
    repetitions: int


def sm2_update(
    state: Sm2State,
    quality: int,
    *,
    # more frequent reviews (default cap)
    max_interval_days: int = 21,

    # learning phase steps (first successes)
    learning_steps: tuple[int, ...] = (1, 2, 4, 7),

    # gentler EF bounds
    min_ef: float = 1.3,
    max_ef: float = 2.4,

    # slow reminding growth
    interval_multiplier: float = 0.85,

    # optional randomness
    fuzz: float = 0.05,
) -> Sm2State:
    """
    Vocab-friendly SM-2 variant:
    - Wrong (q<3): reset reps, short interval
    - Right (q>=3): use learning steps for first N successes
    - After learning: grow interval gently and cap it
    """
    q = max(0, min(int(quality), 5))

    ef = float(state.ease_factor or 2.2)
    interval = int(state.interval_days or 0)
    reps = int(state.repetitions or 0)

    if q < 3:
        # WRONG -> see it again soon
        reps = 0
        interval = 0
        # make it a bit harder next time
        ef = max(min_ef, ef - 0.15)
    else:
        reps += 1

        # learning steps: 1,2,4,7 days
        if reps <= len(learning_steps):
            interval = learning_steps[reps - 1]
        else:
            # gentle growth after graduation
            interval = max(1, int(round(interval * ef * interval_multiplier)))

        # small EF adjustment for success
        ef = min(max_ef, ef + 0.05)

    # guardrails
    interval = min(max_interval_days, max(1, interval))

    # fuzz (optional)
    if interval > 2 and fuzz > 0:
        interval = int(round(interval * (1 + random.uniform(-fuzz, fuzz))))
        interval = min(max_interval_days, max(1, interval))

    return Sm2State(ease_factor=ef, interval_days=interval, repetitions=reps)
