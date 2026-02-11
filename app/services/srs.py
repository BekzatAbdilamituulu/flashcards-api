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
    max_interval_days: int = 365,
    min_ef: float = 1.3,
    max_ef: float = 2.7,
    fuzz: float = 0.08,  # 8% randomness
) -> Sm2State:
    q = max(0, min(int(quality), 5))

    ef = float(state.ease_factor or 2.5)
    interval = int(state.interval_days or 0)
    reps = int(state.repetitions or 0)

    if q < 3:
        reps = 0
        interval = 1
    else:
        reps += 1
        if reps == 1:
            interval = 1
        elif reps == 2:
            interval = 6
        else:
            interval = max(1, int(round(interval * ef)))

    # EF update
    ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ef = max(min_ef, min(max_ef, ef))

    # interval guardrails + fuzz
    interval = min(max_interval_days, max(1, interval))
    if interval > 1:
        interval = int(round(interval * (1 + random.uniform(-fuzz, fuzz))))
        interval = min(max_interval_days, max(1, interval))

    return Sm2State(ease_factor=ef, interval_days=interval, repetitions=reps)
