
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List


# ----------------- CARD SECTION -----------------

class CardBase(BaseModel):
    front: str
    back: str
    example_sentence: Optional[str] = None


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    front: Optional[str] = None
    back: Optional[str] = None
    example_sentence: Optional[str] = None


class CardOut(CardBase):
    id: int
    deck_id: int
    model_config = ConfigDict(from_attributes=True)


# --------------- LANGUAGE SECTION -------------------

class LanguageBase(BaseModel):
    name: str
    code: Optional[str] = None


class LanguageCreate(LanguageBase):
    pass


class LanguageUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None


class LanguageOut(LanguageBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ----------------- DECK SECTION -----------------

class DeckBase(BaseModel):
    name: str
    source_language_id: int
    target_language_id: int


class DeckCreate(DeckBase):
    pass


class DeckOut(DeckBase):
    id: int
    is_public: bool = False
    status: str = "draft"
    shared_code: Optional[str] = None
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# ----------------- USER SECTION -----------------

class RegisterIn(BaseModel):
    username: str
    password: str = Field(min_length=1, max_length=64)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


# ----------------- STUDY / PROGRESS -----------------

class UserCardProgressOut(BaseModel):
    user_id: int
    card_id: int
    times_seen: int
    times_correct: int
    status: str

    ease_factor: Optional[float] = None
    interval_days: Optional[int] = None
    repetitions: Optional[int] = None
    last_review: Optional[datetime] = None
    next_review: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StudyAnswerIn(BaseModel):
    correct: Optional[bool] = None
    quality: Optional[int] = Field(default=None, ge=0, le=5)


class StudyBatchOut(BaseModel):
    deck_id: int
    count: int
    cards: List[CardOut]


class StudyStatusOut(BaseModel):
    deck_id: int
    due_count: int
    new_available_count: int
    reviewed_today: int
    new_introduced_today: int
    remaining_review_quota: int
    remaining_new_quota: int
    next_due_at: Optional[datetime] = None