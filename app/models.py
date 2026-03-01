from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # user goals
    daily_card_target = Column(Integer, default=20, nullable=False)
    daily_new_target = Column(Integer, default=7, nullable=False)

    # relationships
    decks = relationship("Deck", back_populates="owner", cascade="all, delete-orphan")
    shared_decks = relationship("DeckAccess", back_populates="user", cascade="all, delete-orphan")


class UserLearningPair(Base):
    __tablename__ = "user_learning_pairs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_language_id = Column(Integer, ForeignKey("languages.id"), nullable=False)
    target_language_id = Column(Integer, ForeignKey("languages.id"), nullable=False)

    is_default = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", backref="learning_pairs")
    source_language = relationship("Language", foreign_keys=[source_language_id])
    target_language = relationship("Language", foreign_keys=[target_language_id])

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_language_id",
            "target_language_id",
            name="uq_user_learning_pairs_user_src_tgt",
        ),
        Index("ix_user_learning_pairs_user_default", "user_id", "is_default"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

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


class DeckType(enum.Enum):
    MAIN = "main"
    USERS = "users"
    LIBRARY = "library"


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
    shared_code = Column(
        String, nullable=True, unique=True
    )  # generate on publish or on "create share link"

    # deck type
    #'main' main deck user can study
    # "user"    - user deck only storage
    # "library" - admin-created, read-only for normal users; users import cards into their own decks
    deck_type = Column(String, default=DeckType.MAIN, nullable=False, index=True)

    # language pair
    source_language_id = Column(Integer, ForeignKey("languages.id"), nullable=False)
    target_language_id = Column(Integer, ForeignKey("languages.id"), nullable=False)

    source_language = relationship("Language", foreign_keys=[source_language_id])
    target_language = relationship("Language", foreign_keys=[target_language_id])

    # content
    cards = relationship("Card", back_populates="deck", cascade="all, delete-orphan")

    # permissions
    user_permissions = relationship(
        "DeckAccess", back_populates="deck", cascade="all, delete-orphan"
    )


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

    __table_args__ = (UniqueConstraint("deck_id", "user_id", name="uq_deck_access_deck_user"),)

    deck = relationship("Deck", back_populates="user_permissions")
    user = relationship("User", back_populates="shared_decks")


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    front = Column(String, nullable=False)
    front_norm = Column(String, nullable=False, index=True)
    back = Column(String, nullable=True)
    example_sentence = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False, index=True)
    deck = relationship("Deck", back_populates="cards")

    __table_args__ = (UniqueConstraint("deck_id", "front_norm", name="uq_cards_deck_front_norm"),)


class UserCardProgress(Base):
    """
    Per-user SM-2 progress for a specific card.
    """

    __tablename__ = "user_card_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False, index=True)
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

    learning_pair_id = Column(
        Integer,
        ForeignKey("user_learning_pairs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    date = Column(Date, nullable=False, index=True)

    cards_done = Column(Integer, default=0)
    reviews_done = Column(Integer, default=0)
    new_done = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "learning_pair_id", "date", name="uq_daily_progress_user_pair_date"
        ),
        Index("ix_daily_progress_user_pair_date", "user_id", "learning_pair_id", "date"),
    )


# Translation
class TranslationCache(Base):
    __tablename__ = "translation_cache"

    id = Column(Integer, primary_key=True)

    # what was translated
    src_language_id = Column(Integer, ForeignKey("languages.id"), nullable=False, index=True)
    tgt_language_id = Column(Integer, ForeignKey("languages.id"), nullable=False, index=True)
    source_text = Column(String, nullable=False)
    source_text_norm = Column(String, nullable=False, index=True)

    translated_text = Column(String, nullable=False)
    provider = Column(String, default="mymemory", nullable=False)

    hits = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "src_language_id",
            "tgt_language_id",
            "source_text_norm",
            "provider",
            name="uq_translation_cache_src_tgt_text_provider",
        ),
        Index(
            "ix_translation_cache_src_tgt_text",
            "src_language_id",
            "tgt_language_id",
            "source_text_norm",
        ),
    )


class ExampleSentenceCache(Base):
    __tablename__ = "example_sentence_cache"

    id = Column(Integer, primary_key=True)

    # query word/phrase (usually card.front)
    src_language_id = Column(Integer, ForeignKey("languages.id"), nullable=False, index=True)
    tgt_language_id = Column(Integer, ForeignKey("languages.id"), nullable=False, index=True)
    query_text = Column(String, nullable=False)
    query_text_norm = Column(String, nullable=False, index=True)

    # store one "best" example (you can extend later to multiple)
    example_text = Column(Text, nullable=False)
    provider = Column(String, default="tatoeba", nullable=False)

    hits = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "src_language_id",
            "tgt_language_id",
            "query_text_norm",
            "provider",
            name="uq_example_cache_src_tgt_query_provider",
        ),
        Index(
            "ix_example_cache_src_tgt_query",
            "src_language_id",
            "tgt_language_id",
            "query_text_norm",
        ),
    )
