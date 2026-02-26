
from __future__ import annotations
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from typing import Optional, List, Generic, TypeVar
from enum import Enum

class LoginIn(BaseModel):
    username: str
    password: str

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
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InboxWordIn(BaseModel):
    front: str = Field(min_length=1, max_length=200)
    back: Optional[str] = Field(default=None, max_length=500)
    example_sentence: Optional[str] = Field(default=None, max_length=500)

    # optional: allow client to define languages for Inbox creation
    source_language_id: Optional[int] = None
    target_language_id: Optional[int] = None

class InboxWordOut(BaseModel):
    deck_id: int
    card: CardOut 


class InboxBulkIn(BaseModel):
    text: str = Field(..., examples=[""])
    delimiter: Optional[str] = Field(default=None, examples=["—", "-", ":", "	"])
    # Optional: if user's defaults are not set yet, you may pass language IDs here.
    source_language_id: Optional[int] = Field(default=None, ge=1)
    target_language_id: Optional[int] = Field(default=None, ge=1)
    dry_run: bool = False

class BulkItemResult(BaseModel):
    line: str
    status: str  # "created" | "skipped" | "failed"
    reason: Optional[str] = None
    card_id: Optional[int] = None

class InboxBulkOut(BaseModel):
    deck_id: int
    created: int
    skipped: int
    failed: int
    results: List[BulkItemResult]



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

class UserSetLanguagesIn(BaseModel):
    default_source_language_id: int
    default_target_language_id: int

class UserLearningPairCreateIn(BaseModel):
    source_language_id: int
    target_language_id: int
    make_default: bool = True

class UserLearningPairOut(BaseModel):
    id: int
    source_language_id: int
    target_language_id: int
    is_default: bool

    model_config = ConfigDict(from_attributes=True)


# ----------------- DECK SECTION -----------------

class DeckBase(BaseModel):
    name: str
    source_language_id: int
    target_language_id: int
    deck_type: str = "users"  # "main" | "users" | "library"


class DeckCreate(DeckBase):
    pass


class DeckOut(DeckBase):
    id: int
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class DeckUpdate(BaseModel):
    name: Optional[str] = None
    is_public: Optional[bool] = None

class DeckStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"

# ----------------- LIBRARY -----------------

class LibraryDeckOut(BaseModel):
    id: int
    name: str
    source_language_id: int
    target_language_id: int
    deck_type: str  # "library"
    cards_count: int


class ImportCardIn(BaseModel):
    target_deck_id: int = Field(ge=1)


class ImportCardOut(BaseModel):
    imported: bool
    skipped: bool
    reason: Optional[str] = None
    card: Optional[CardOut] = None


# ----------------- USER SECTION -----------------

class RegisterIn(BaseModel):
    username: str
    password: str = Field(min_length=1, max_length=64)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    username: str
    daily_card_target: int
    daily_new_target: int
    model_config = ConfigDict(from_attributes=True)


class UserLanguageDefaultsIn(BaseModel):
    default_source_language_id: int = Field(ge=1)
    default_target_language_id: int = Field(ge=1)




# ----------------- STUDY / PROGRESS -----------------
class ProgressStatus(str, Enum):
    NEW = "new"
    LEARNING = "learning"
    MASTERED = "mastered"

class UserCardProgressOut(BaseModel):
    user_id: int
    card_id: int
    times_seen: int
    times_correct: int
    status: ProgressStatus  # new | learning | mastered

    stage: Optional[int] = None      # 1..5 when learning
    last_review: Optional[datetime] = None
    due_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StudyAnswerIn(BaseModel):
    learned: bool


class StudyQueueItemOut(BaseModel):
    type: str  # "review" | "new"
    card: CardOut


class StudyBatchOut(BaseModel):
    deck_id: int
    count: int
    cards: List[CardOut]

    # Optional: include current quotas/counters like /study/status
    meta: Optional["StudyStatusOut"] = None


class StudyStatusOut(BaseModel):
    deck_id: int
    due_count: int
    new_available_count: int
    reviewed_today: int
    new_introduced_today: int
    remaining_review_quota: int
    remaining_new_quota: int
    next_due_at: Optional[datetime] = None

T = TypeVar("T")

class PageMeta(BaseModel):
    limit: int 
    offset: int 
    total: int 
    has_more: bool

class Page(BaseModel, Generic[T]):
    items: List[T]
    meta: PageMeta


class DailyProgressOut(BaseModel):
    date: date
    cards_done: int
    reviews_done: int
    new_done: int

class DailyProgressRangeOut(BaseModel):
    from_date: date
    to_date: date
    items: list[DailyProgressOut]

class StreakOut(BaseModel):
    current_streak: int
    best_streak: int
    threshold: int = 10

class TodayAddedOut(BaseModel):
    date: date
    count: int

class ProgressSummaryOut(BaseModel):
    date: date  # Bishkek today

    # Today metrics
    today_cards_done: int
    today_reviews_done: int
    today_new_done: int
    today_added_cards: int

    # Streak (threshold-based)
    current_streak: int
    best_streak: int
    streak_threshold: int

    # Study queue info (optional deck_id filter)
    due_count: int
    new_available_count: int
    next_due_at: Optional[datetime] = None

    # Progress totals (optional deck_id filter)
    total_cards: int
    total_mastered: int
    total_learning: int
    total_new: int