from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
	__tablename__ = 'users'
	id = Column(Integer, primary_key=True, index=True)
	username = Column(String, unique=True, index=True, nullable=False)
	hashed_password = Column(String, nullable=False)
	created_at = Column(DateTime, default=datetime.utcnow)

class Language(Base):
	__tablename__ = 'languages'
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String, unique=True) #English
	code = Column(String)


class Word(Base):
	__tablename__ = 'words'
	id = Column(Integer, primary_key=True, index=True)
	text = Column(String, nullable=False)
	translation = Column(String,nullable=False)
	example_sentence = Column(String)
	language_id = Column(Integer, ForeignKey("languages.id"))

class UserWord(Base):
    """Tracks progress of a specific word for a specific user"""
    __tablename__ = "user_words"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    word_id = Column(Integer, ForeignKey("words.id"))
    status = Column(String, default="new") # e.g., learning, mastered
    times_seen = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    last_review = Column(DateTime)

