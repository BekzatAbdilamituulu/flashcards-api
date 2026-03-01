from __future__ import annotations

import asyncio
import os
import re
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from .. import models

# ==============================
# Utils
# ==============================

_SPACE_RE = re.compile(r"\s+", re.UNICODE)


def norm(text: str) -> str:
    return _SPACE_RE.sub(" ", (text or "").strip()).lower()


ISO2_TO_TATOEBA = {
    "en": "eng",
    "ru": "rus",
    "ky": "kir",
    "tr": "tur",
    "de": "deu",
    "fr": "fra",
    "es": "spa",
    "it": "ita",
    "pt": "por",
    "zh": "cmn",
    "ja": "jpn",
    "ko": "kor",
    "ar": "ara",
}


def _tatoeba_lang(code: str) -> Optional[str]:
    if not code:
        return None
    c = code.strip().lower()
    if len(c) == 3:
        return c
    if len(c) == 2:
        return ISO2_TO_TATOEBA.get(c)
    return None


# ==============================
# Sync HTTP (used by crud.create_card)
# ==============================


def fetch_mymemory_translation(*, text: str, src_code: str, tgt_code: str) -> Optional[str]:
    url = "https://api.mymemory.translated.net/get"
    params = {"q": text, "langpair": f"{src_code}|{tgt_code}", "mt": 1}

    de_email = os.getenv("MYMEMORY_DE_EMAIL")
    if de_email:
        params["de"] = de_email

    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return None

    translated = (data.get("responseData") or {}).get("translatedText")
    translated = (translated or "").strip()
    return translated or None


def fetch_tatoeba_example(*, query: str, src_code: str, tgt_code: str) -> Optional[str]:
    url = "https://tatoeba.org/en/api_v0/search"
    params = {"from": src_code, "query": query, "to": tgt_code, "sort": "relevance"}

    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return None

    results = data.get("results")
    if not isinstance(results, list) or not results:
        return None

    first = results[0]
    src_text = (first.get("text") or "").strip()
    translations = first.get("translations") or []

    tgt_text = ""
    if isinstance(translations, list) and translations:
        t0 = translations[0]
        if isinstance(t0, dict):
            tgt_text = (t0.get("text") or "").strip()

    if tgt_text:
        return f"{src_text}\n{tgt_text}".strip()
    return src_text or None


# ==============================
# Cache (sync DB)
# ==============================


def find_cached_translation(db: Session, *, src_lang_id: int, tgt_lang_id: int, text_raw: str):
    key = norm(text_raw)
    row = (
        db.query(models.TranslationCache)
        .filter(
            models.TranslationCache.src_language_id == src_lang_id,
            models.TranslationCache.tgt_language_id == tgt_lang_id,
            models.TranslationCache.source_text_norm == key,
        )
        .first()
    )
    return row.translated_text if row else None


def save_translation_cache(
    db: Session, *, src_lang_id: int, tgt_lang_id: int, text_raw: str, translation: str
):
    row = models.TranslationCache(
        src_language_id=src_lang_id,
        tgt_language_id=tgt_lang_id,
        source_text=text_raw,
        source_text_norm=norm(text_raw),
        translated_text=translation,
        provider="mymemory",
        hits=0,
    )
    db.add(row)
    db.commit()


def find_cached_example(db: Session, *, src_lang_id: int, tgt_lang_id: int, text_raw: str):
    key = norm(text_raw)
    row = (
        db.query(models.ExampleSentenceCache)
        .filter(
            models.ExampleSentenceCache.src_language_id == src_lang_id,
            models.ExampleSentenceCache.tgt_language_id == tgt_lang_id,
            models.ExampleSentenceCache.query_text_norm == key,
        )
        .first()
    )
    return row.example_text if row else None


def save_example_cache(
    db: Session, *, src_lang_id: int, tgt_lang_id: int, text_raw: str, example_text: str
):
    row = models.ExampleSentenceCache(
        src_language_id=src_lang_id,
        tgt_language_id=tgt_lang_id,
        query_text=text_raw,
        query_text_norm=norm(text_raw),
        example_text=example_text,
        provider="tatoeba",
        hits=0,
    )
    db.add(row)
    db.commit()


# ==============================
# Public sync API (used by crud)
# ==============================


def get_translation_with_cache(
    db: Session, *, src_lang: models.Language, tgt_lang: models.Language, text_raw: str
):
    cached = find_cached_translation(
        db, src_lang_id=src_lang.id, tgt_lang_id=tgt_lang.id, text_raw=text_raw
    )
    if cached:
        return cached

    if not src_lang.code or not tgt_lang.code:
        return None

    translated = fetch_mymemory_translation(
        text=text_raw, src_code=src_lang.code, tgt_code=tgt_lang.code
    )
    if translated:
        save_translation_cache(
            db,
            src_lang_id=src_lang.id,
            tgt_lang_id=tgt_lang.id,
            text_raw=text_raw,
            translation=translated,
        )
    return translated


def get_example_with_cache(
    db: Session, *, src_lang: models.Language, tgt_lang: models.Language, text_raw: str
):
    cached = find_cached_example(
        db, src_lang_id=src_lang.id, tgt_lang_id=tgt_lang.id, text_raw=text_raw
    )
    if cached:
        return cached

    src_code = _tatoeba_lang(src_lang.code or "")
    tgt_code = _tatoeba_lang(tgt_lang.code or "")
    if not src_code or not tgt_code:
        return None

    ex = fetch_tatoeba_example(query=text_raw, src_code=src_code, tgt_code=tgt_code)
    if ex:
        save_example_cache(
            db, src_lang_id=src_lang.id, tgt_lang_id=tgt_lang.id, text_raw=text_raw, example_text=ex
        )
    return ex


# ==============================
# Async preview (parallel)
# ==============================


async def fetch_mymemory_translation_async(*, text: str, src_code: str, tgt_code: str):
    url = "https://api.mymemory.translated.net/get"
    params = {"q": text, "langpair": f"{src_code}|{tgt_code}", "mt": 1}

    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    translated = (data.get("responseData") or {}).get("translatedText")
    translated = (translated or "").strip()
    return translated or None


async def fetch_tatoeba_example_async(*, query: str, src_code: str, tgt_code: str):
    url = "https://tatoeba.org/en/api_v0/search"
    params = {"from": src_code, "query": query, "to": tgt_code, "sort": "relevance"}

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    results = data.get("results")
    if not isinstance(results, list) or not results:
        return None

    first = results[0]
    src_text = (first.get("text") or "").strip()
    translations = first.get("translations") or []

    tgt_text = ""
    if isinstance(translations, list) and translations:
        t0 = translations[0]
        if isinstance(t0, dict):
            tgt_text = (t0.get("text") or "").strip()

    if tgt_text:
        return f"{src_text}\n{tgt_text}".strip()
    return src_text or None


async def get_preview_with_cache_async(db: Session, *, src_lang, tgt_lang, text_raw):
    tr_cached = find_cached_translation(
        db, src_lang_id=src_lang.id, tgt_lang_id=tgt_lang.id, text_raw=text_raw
    )
    ex_cached = find_cached_example(
        db, src_lang_id=src_lang.id, tgt_lang_id=tgt_lang.id, text_raw=text_raw
    )

    if tr_cached is not None and ex_cached is not None:
        return tr_cached, ex_cached

    tr_task = fetch_mymemory_translation_async(
        text=text_raw, src_code=src_lang.code, tgt_code=tgt_lang.code
    )
    src_code = _tatoeba_lang(src_lang.code or "")
    tgt_code = _tatoeba_lang(tgt_lang.code or "")
    ex_task = fetch_tatoeba_example_async(query=text_raw, src_code=src_code, tgt_code=tgt_code)

    tr_new, ex_new = await asyncio.gather(tr_task, ex_task)

    if tr_new:
        save_translation_cache(
            db,
            src_lang_id=src_lang.id,
            tgt_lang_id=tgt_lang.id,
            text_raw=text_raw,
            translation=tr_new,
        )
    if ex_new:
        save_example_cache(
            db,
            src_lang_id=src_lang.id,
            tgt_lang_id=tgt_lang.id,
            text_raw=text_raw,
            example_text=ex_new,
        )

    return tr_new or tr_cached, ex_new or ex_cached
