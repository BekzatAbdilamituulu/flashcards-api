from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    username: str
    password: str


class GoogleAuthIn(BaseModel):
    id_token: str = Field(min_length=1)


class ContentKind(str, Enum):
    WORD = "word"
    PHRASE = "phrase"
    QUOTE = "quote"
    IDEA = "idea"


# ----------------- CARD SECTION -----------------


class CardBase(BaseModel):
    front: str
    back: str
    example_sentence: Optional[str] = None
    content_kind: Optional[ContentKind] = None
    reading_source_id: Optional[int] = None
    source_title: Optional[str] = None
    source_author: Optional[str] = None
    source_kind: Optional[str] = None
    source_reference: Optional[str] = None
    source_sentence: Optional[str] = None
    source_page: Optional[str] = None
    context_note: Optional[str] = None


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    front: Optional[str] = None
    back: Optional[str] = None
    example_sentence: Optional[str] = None
    content_kind: Optional[ContentKind] = None
    reading_source_id: Optional[int] = None
    source_title: Optional[str] = None
    source_author: Optional[str] = None
    source_kind: Optional[str] = None
    source_reference: Optional[str] = None
    source_sentence: Optional[str] = None
    source_page: Optional[str] = None
    context_note: Optional[str] = None


class ReadingSourceBase(BaseModel):
    title: str
    author: Optional[str] = None
    kind: Optional[str] = None
    reference: Optional[str] = None


class ReadingSourceCreate(ReadingSourceBase):
    pair_id: int


class ReadingSourceUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    kind: Optional[str] = None
    reference: Optional[str] = None


class ReadingSourceOut(ReadingSourceBase):
    id: int
    user_id: int
    pair_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReadingSourceOutWithStats(ReadingSourceOut):
    total_cards: int = 0
    due_cards: int = 0
    added_today: int = 0
    last_added_at: Optional[datetime] = None


class SourceDetailOut(BaseModel):
    source: ReadingSourceOutWithStats
    cards: List["CardOut"]
    meta: "PageMeta"


class CardOut(CardBase):
    id: int
    deck_id: int
    created_at: datetime
    reading_source: Optional[ReadingSourceOut] = None
    memory_strength: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CardWithStatusOut(CardOut):
    status: str = "new"


class InboxWordIn(BaseModel):
    front: str = Field(min_length=1, max_length=200)
    back: Optional[str] = Field(default=None, max_length=500)
    example_sentence: Optional[str] = Field(default=None, max_length=500)
    reading_source_id: Optional[int] = Field(default=None, ge=1)
    source_title: Optional[str] = Field(default=None, max_length=300)
    source_author: Optional[str] = Field(default=None, max_length=200)
    source_kind: Optional[str] = Field(default=None, max_length=50)
    source_reference: Optional[str] = Field(default=None, max_length=1000)
    source_sentence: Optional[str] = Field(default=None, max_length=1000)
    source_page: Optional[str] = Field(default=None, max_length=100)
    context_note: Optional[str] = Field(default=None, max_length=1000)

    # optional: allow client to define languages for Inbox creation
    source_language_id: Optional[int] = None
    target_language_id: Optional[int] = None

class ImportSelectedCardsIn(BaseModel):
    card_ids: list[int]
    dry_run: bool = False

class ImportSelectedCardItemOut(BaseModel):
    library_card_id: int
    status: str
    imported: bool
    skipped: bool
    reason: str | None = None
    card: CardOut | None = None


class ImportSelectedCardsOut(BaseModel):
    results: list[ImportSelectedCardItemOut]
    created_count: int
    preview_count: int
    duplicate_count: int
    invalid_count: int
    failed_count: int
    imported_count: int
    skipped_count: int

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
    index: int
    line: str
    front: Optional[str] = None
    status: str  # "preview" | "created" | "duplicate" | "invalid" | "failed"
    reason: Optional[str] = None
    card_id: Optional[int] = None


class InboxBulkOut(BaseModel):
    deck_id: int
    created_count: int
    preview_count: int
    duplicate_count: int
    invalid_count: int
    failed_count: int
    # Legacy fields kept for compatibility.
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
    name: str
    code: str

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
    source_language: LanguageOut
    target_language: LanguageOut

    model_config = ConfigDict(from_attributes=True)


# ----------------- DECK SECTION -----------------


class DeckBase(BaseModel):
    name: str
    source_language_id: int
    target_language_id: int


class DeckCreate(BaseModel):
    name: str
    pair_id: int | None = None
    source_language_id: int | None = None
    target_language_id: int | None = None
    source_type: Optional[str] = None
    author_name: Optional[str] = None

class DeckOut(DeckBase):
    id: int
    deck_type: str
    source_type: Optional[str] = None
    author_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class DeckUpdate(BaseModel):
    name: Optional[str] = None
    is_public: Optional[bool] = None
    source_type: Optional[str] = None
    author_name: Optional[str] = None


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
    dry_run: bool = False


class ImportCardOut(BaseModel):
    status: str
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
    email: Optional[str] = None
    email_verified: bool
    daily_card_target: int
    daily_new_target: int
    model_config = ConfigDict(from_attributes=True)


class UserLanguageDefaultsIn(BaseModel):
    default_source_language_id: int = Field(ge=1)
    default_target_language_id: int = Field(ge=1)

class UserGoalIn(BaseModel):
    daily_card_target: int = Field(ge=1, le=500)
    daily_new_target: int = Field(ge=0, le=200)


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

    stage: Optional[int] = None  # 1..5 when learning
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

    #Daily goals (targets)
    daily_card_target: int
    daily_new_target: int

    #Daily goals progress (computed)
    cards_remaining: int
    new_remaining: int
    cards_goal_pct: float
    new_goal_pct: float

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


class AutoPreviewIn(BaseModel):
    front: str
    deck_id: Optional[int] = None
    source_language_id: Optional[int] = None
    target_language_id: Optional[int] = None


class AutoProvidersOut(BaseModel):
    translation: Optional[str] = None
    example: Optional[str] = None


class AutoCachedOut(BaseModel):
    translation: bool = False
    example: bool = False


class AutoPreviewOut(BaseModel):
    front: str
    suggested_back: Optional[str] = None
    suggested_example_sentence: Optional[str] = None
    provider: AutoProvidersOut
    cached: AutoCachedOut
