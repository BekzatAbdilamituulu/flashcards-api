from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple, List

MASTERED = 3

def compute_status(times_seen: int, times_correct: int) -> str:
	if times_correct >= MASTERED:
		return 'mastered'
	if times_seen <= 0:
		return 'new'
	return 'learning'

def hours_since(dt: Optional[datetime]) -> float:
	if not dt:
		return 1e9 # never reviewed 
	if dt.tzinfo is None:
		dt = dt.replace(tzinfo=timezone.utc)
	now = datetime.now(timezone.utc)
	return max((now - dt).total_seconds() / 3600.0, 0.0)


def score_word(times_seen: int, times_correct: int, last_review: Optional[datetime]) -> float:
    seen = max(times_seen or 0, 0)
    correct = max(times_correct or 0, 0)
    acc = (correct/seen) if seen > 0 else 0.0

    age_h = hours_since(last_review)

    status = compute_status(seen, correct)

    #Base weight by status
    if status == 'learning':
    	status_w = 1.0
    elif status =='new':
    	status_w = 0.7
    else: #mastered
    	status_w = 0.15

    #Want low accuracy + old reviews
    difficulty = 1.0 - acc
    recency_boot = min(age_h / 24.0, 7.0) # up to 7 days weight

    #Slight penalty for being seen many times ( so it doesnt loop forever)
    fatigue_penalty = min(seen * 0.05, 1.0)

    return status_w * (1.0 + 1.5 * difficulty + recency_boot) - fatigue_penalty
