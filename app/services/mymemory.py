import os
import json
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


MYMEMORY_BASE_URL = "https://api.mymemory.translated.net/get"


class MyMemoryError(RuntimeError):
    pass


def translate(text: str, source_lang: str, target_lang: str, *, email: str | None = None, timeout: int = 10) -> str:
    """Translate text using MyMemory.

    Notes:
    - Free tier has limits; passing email (MYMEMORY_EMAIL) increases quota per their docs.
    - MyMemory may return matches; we primarily use responseData.translatedText.
    """
    if not text.strip():
        return ""

    params = {
        "q": text,
        "langpair": f"{source_lang}|{target_lang}",
    }
    if email:
        params["de"] = email

    url = f"{MYMEMORY_BASE_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "flashcards-api/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as e:
        raise MyMemoryError(f"MyMemory request failed: {e}") from e
    except json.JSONDecodeError as e:
        raise MyMemoryError("MyMemory returned invalid JSON") from e

    translated = (data.get("responseData") or {}).get("translatedText")
    if not translated:
        # Sometimes MyMemory returns warnings/errors in responseDetails
        details = data.get("responseDetails")
        raise MyMemoryError(f"MyMemory translation missing. Details: {details!r}")

    return translated