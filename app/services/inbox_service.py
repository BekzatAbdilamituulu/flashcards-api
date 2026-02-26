from __future__ import annotations

from typing import Optional, Tuple
from sqlalchemy.orm import Session

from .. import models
import re

# Matches: em dash, en dash, minus sign, hyphen variants, colon, semicolon, equals, tab, pipe
SPLIT_RE = re.compile(r"\s*(?:—|–|−|-|‐|:|;|=|\t|\|)\s*", re.UNICODE)

def _split_line(line: str, fixed_delim: Optional[str]) -> Optional[Tuple[str, str]]:
    raw = (line or "").strip()
    if not raw or raw.startswith("#"):
        return None

    if fixed_delim:
        if fixed_delim not in raw:
            return None
        left, right = raw.split(fixed_delim, 1)
        front = left.strip()
        back = right.strip()
        if not front:
            return None
        return front, back

    parts = SPLIT_RE.split(raw, maxsplit=1)
    if len(parts) == 2:
        front, back = parts[0].strip(), parts[1].strip()
        if not front:
            return None
        return front, back

    # no delimiter -> front only
    return raw, ""


INBOX_DECK_NAME = "Inbox"

from typing import Optional, Tuple
from sqlalchemy.orm import Session

def resolve_language_pair(
    db: Session,
    user: "models.User",
    *,
    source_language_id: Optional[int],
    target_language_id: Optional[int],
    require_pair_exists: bool = True,
) -> Tuple[int, int]:
    """
    Rules:
    1) If both source & target provided -> use them (validate)
       - if require_pair_exists=True and pair doesn't exist -> auto-create (inbox-friendly)
    2) Else use default UserLearningPair (is_default=True)
    3) Else use legacy user.default_source_language_id / default_target_language_id (if still present)
    4) Else -> error
    """

    src_provided = source_language_id is not None
    tgt_provided = target_language_id is not None

    # If only one is provided -> error (client bug)
    if src_provided ^ tgt_provided:
        raise ValueError("Provide BOTH source_language_id and target_language_id, or provide neither.")

    # Case 1 — explicit pair in payload
    if src_provided and tgt_provided:
        if source_language_id == target_language_id:
            raise ValueError("source_language_id and target_language_id must be different")

        if require_pair_exists:
            pair = (
                db.query(models.UserLearningPair)
                .filter(
                    models.UserLearningPair.user_id == user.id,
                    models.UserLearningPair.source_language_id == source_language_id,
                    models.UserLearningPair.target_language_id == target_language_id,
                )
                .first()
            )
            if not pair:
                # auto-create pair (NOT default)
                pair = models.UserLearningPair(
                    user_id=user.id,
                    source_language_id=source_language_id,
                    target_language_id=target_language_id,
                    is_default=False,
                )
                db.add(pair)
                db.commit()

        return source_language_id, target_language_id

    # Case 2 — default learning pair
    pair = (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == user.id,
            models.UserLearningPair.is_default.is_(True),
        )
        .first()
    )
    if pair:
        return pair.source_language_id, pair.target_language_id

    # Case 3 — legacy fallback (if your User still has these fields)
    legacy_src = getattr(user, "default_source_language_id", None)
    legacy_tgt = getattr(user, "default_target_language_id", None)

    if legacy_src is not None and legacy_tgt is not None:
        if legacy_src == legacy_tgt:
            raise ValueError("Legacy default languages are invalid (source == target)")
        return legacy_src, legacy_tgt

    # Case 4 — nothing configured
    raise ValueError(
        "No default language pair. Set it via /users/me/learning-pairs "
        "or include source_language_id and target_language_id in request."
    )

