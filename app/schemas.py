from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

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
	correct: bool

#-----------Deck

class DeckItemOut(BaseModel):
	word: WordOut
	status: str = 'new'
	times_seen: int=0
	times_correct: int=0
	last_review: Optional[datetime] = None