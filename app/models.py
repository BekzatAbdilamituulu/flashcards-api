
from __future__ import annotations

from datetime import datetime, timezone
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # user goals
    daily_card_target = Column(Integer, default=20, nullable=False)
    daily_new_target = Column(Integer, default=7, nullable=False)

    default_source_language_id = Column(Integer, ForeignKey("languages.id"), nullable=True)
    default_target_language_id = Column(Integer, ForeignKey("languages.id"), nullable=True)

    # relationships
    decks = relationship("Deck", back_populates="owner", cascade="all, delete-orphan")
    shared_decks = relationship("DeckAccess", back_populates="user", cascade="all, delete-orphan")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # jti is inside JWT; unique per refresh token
    jti = Column(String(36), nullable=False, unique=True, index=True)

    # store only hash of refresh token (never store raw token)
    token_hash = Column(String(64), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="refresh_tokens")

Index("ix_refresh_tokens_user_revoked", RefreshToken.user_id, RefreshToken.revoked_at)


class Language(Base):
    """
    Global/admin-managed. Do NOT attach to a user.
    """
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # English
    code = Column(String, unique=True, nullable=True)  # en


class DeckStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    HIDDEN = "hidden"


class Deck(Base):
    __tablename__ = "decks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    # creator/owner (for moderation / editing)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner = relationship("User", back_populates="decks")

    # sharing
    is_public = Column(Boolean, default=False, nullable=False)
    status = Column(Enum(DeckStatus), default=DeckStatus.DRAFT, nullable=False)
    shared_code = Column(String, nullable=True, unique=True)  # generate on publish or on "create share link"

    # deck type
    # "user"    - normal user deck
    # "library" - admin-created, read-only for normal users; users import cards into their own decks
    deck_type = Column(String, default="user", nullable=False, index=True)

    # language pair
    source_language_id = Column(Integer, ForeignKey("languages.id"), nullable=False)
    target_language_id = Column(Integer, ForeignKey("languages.id"), nullable=False)

    source_language = relationship("Language", foreign_keys=[source_language_id])
    target_language = relationship("Language", foreign_keys=[target_language_id])

    # content
    cards = relationship("Card", back_populates="deck", cascade="all, delete-orphan")

    # permissions
    user_permissions = relationship("DeckAccess", back_populates="deck", cascade="all, delete-orphan")


class DeckRole(enum.Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class DeckAccess(Base):
    __tablename__ = "deck_access"

    id = Column(Integer, primary_key=True)
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    role = Column(Enum(DeckRole), default=DeckRole.VIEWER, nullable=False)

    __table_args__ = (
        UniqueConstraint("deck_id", "user_id", name="uq_deck_access_deck_user"),
    )

    deck = relationship("Deck", back_populates="user_permissions")
    user = relationship("User", back_populates="shared_decks")


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    front = Column(String, nullable=False)
    front_norm = Column(String, nullable=False, index=True)
    back = Column(String, nullable=False)
    example_sentence = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False, index=True)
    deck = relationship("Deck", back_populates="cards")

    __table_args__ = (
        UniqueConstraint("deck_id", "front_norm", name="uq_cards_deck_front_norm"),
    )


class UserCardProgress(Base):
    """
    Per-user SM-2 progress for a specific card.
    """
    __tablename__ = "user_card_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False, index=True)

    status = Column(String, default="new")  # new | learning | mastered
    times_seen = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    last_review = Column(DateTime, nullable=True)

    # 3-state scheduler
    # status: new | learning | mastered
    status = Column(String, default="new", nullable=False)

    # stage only used for "learning" (1..5)
    stage = Column(Integer, nullable=True)

    # next time card is eligible to show (for NEW/LEARNING)
    due_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("user_id", "card_id", name="uq_user_card_progress_user_card"),
        Index("ix_user_card_progress_user_due_at", "user_id", "due_at"),
    )


class DailyProgress(Base):
    __tablename__ = "daily_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    cards_done = Column(Integer, default=0)
    reviews_done = Column(Integer, default=0)
    new_done = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_progress_user_date"),
    )