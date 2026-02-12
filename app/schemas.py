from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List

# ----------------- WORD SECTION -----------------

class WordBase(BaseModel):
    text: str
    translation: str
    language_id: int
    example_sentence: Optional[str] = None


class WordCreate(WordBase):
    pass


class WordUpdate(BaseModel):
    text: Optional[str] = None
    translation: Optional[str] = None
    language_id: Optional[int] = None
    example_sentence: Optional[str] = None


class WordOut(WordBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --------------- LANGUAGE SECTION -------------------

class LanguageBase(BaseModel):
    name: str
    code: str


class LanguageCreate(LanguageBase):
    pass


class LanguageUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None


class LanguageOut(LanguageBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


#-------------------USER SECTION---------------

class RegisterIn(BaseModel):
    username: str
    password: str = Field(min_length=1, max_length=64)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"






class UserCreate(BaseModel):
	username: str
	password: str

class UserOut(BaseModel):
	id: int
	username: str

	model_config = ConfigDict(from_attributes=True)


class UserWordOut(BaseModel):
	word_id: int
	times_seen: int 
	times_correct: int 
	status: str
	
	ease_factor: float | None = None 
	interval_days: int | None = None 
	repetitions: int | None = None 
	next_review: Optional[datetime] = None

	model_config = ConfigDict(from_attributes=True)


#-------------------progress session---------------

class WordProgressOut(BaseModel):
	word: WordOut
	times_seen: int 
	times_correct: int
	status: str
	last_review: Optional[datetime] = None

	model_config = ConfigDict(from_attributes=True)

class ProgressStatsOut(BaseModel):
	language_id: int
	total_tracked: int

	new: int
	learning: int
	mastered: int

	total_seen: int
	total_correct: int
	accuracy: float

class ProgressResetOut(BaseModel):
	user_id: int
	language_id: int
	deleted: int

class NextReviewOut(BaseModel):
	word: WordOut
	score: float
	reason: str
	last_review: Optional[datetime] = None
	times_seen: int = 0 
	times_correct: int = 0
	status: str = "new"
	

class StudyAnswerIn(BaseModel):
	correct: Optional[bool] = None
	quality: Optional[int] = Field(default=None, ge=0, le=5)

#-----------Deck
class DeckOut(BaseModel):
    language_id: int
    count: int
    words: List[WordOut]

class DeckItemOut(BaseModel):
	word: WordOut
	status: str = 'new'
	times_seen: int=0
	times_correct: int=0
	last_review: Optional[datetime] = None

class StatsOut(BaseModel):
    language_id: int
    total_words: int
    learned_words: int
    new_words: int
    learning_words: int
    mastered_words: int
    overdue_words: int

# import export words
class WordImportItem(BaseModel):
	text: str = Field(min_length=1)
	translation: str = Field(min_length=1)
	example_sentence: Optional[str] = None

class WordImportRequest(BaseModel):
	items: List[WordImportItem]


class StudyStatusOut(BaseModel):
    language_id: int
    due_count: int
    new_available_count: int
    reviewed_today: int
    new_introduced_today: int
    remaining_review_quota: int
    remaining_new_quota: int
    next_due_at: Optional[datetime] = None
