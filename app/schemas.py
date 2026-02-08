from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

# -----------------WORD SECTION------------


class WordBase(BaseModel):
	text: str
	translation: str
	language_id: int
	example_sentence: str | None

class WordCreate(WordBase):
	language_id: int
	text: str
	translation: str
	example_sentence: str | None = None

class WordOut(WordBase):
	id: int
	model_config = ConfigDict(from_attributes=True)



#---------------LANGUAGE SECTION-------------------

class LanguageCreate(BaseModel):
	name: str
	code: str

class LanguageOut(BaseModel):
	id: int
	name: str
	code: str 

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
