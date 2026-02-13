from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Date
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
	__tablename__ = 'users'
	id = Column(Integer, primary_key=True, index=True)
	username = Column(String, unique=True, index=True, nullable=False)
	hashed_password = Column(String, nullable=False)
	created_at = Column(DateTime, default=datetime.utcnow)

	languages = relationship("Language", back_populates="owner", cascade="all, delete-orphan")
	words = relationship("Word", back_populates="owner", cascade="all, delete-orphan")
	decks = relationship("Deck", back_populates="owner", cascade="all, delete-orphan")

	#user goals
	daily_card_target = Column(Integer, default=20, nullable=False)
	daily_new_target = Column(Integer, default=7, nullable=False)  # optional limiter

class Language(Base):
	__tablename__ = 'languages'
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String, nullable=False) #English
	code = Column(String)

	owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
	owner = relationship('User', back_populates='languages')

class Deck(Base):
	__tablename__ = 'decks'
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String, nullable=False)

	owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
	owner = relationship('User', back_populates='decks')

	#per-deck language pair
	source_language_id = Column(Integer, ForeignKey('languages.id'), nullable=False)
	target_language_id = Column(Integer, ForeignKey('languages.id'), nullable=False)

	source_language = relationship('Language', foreign_keys=[source_language_id])
	target_language = relationship('Language', foreign_keys=[target_language_id])

	words = relationship("Word", back_populates="deck", cascade="all, delete-orphan")

class Word(Base):
	__tablename__ = 'words'
	id = Column(Integer, primary_key=True, index=True)
	text = Column(String, nullable=False)
	translation = Column(String,nullable=False)
	example_sentence = Column(String)

	owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
	owner = relationship('User', back_populates='words')

	language_id = Column(Integer, ForeignKey("languages.id"))
	language = relationship("Language")

	deck_id = Column(Integer, ForeignKey("decks.id"), nullable=True)
	deck = relationship("Deck", back_populates="words")

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

    # sm-2 sheduling fields
    ease_factor = Column(Float, default=2.5) #ef
    interval_days = Column(Integer, default=0) #current interval (days)
    repetitions = Column(Integer, default=0) #successful reps in a row
    next_review = Column(DateTime, nullable=True)

class DailyProgress(Base):
    __tablename__ = "daily_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    date = Column(Date, index=True)

    cards_done = Column(Integer, default=0)
    reviews_done = Column(Integer, default=0)
    new_done = Column(Integer, default=0)
