def make_example_sentence(term: str, source_lang: str) -> str:
    """Very simple example sentence generator.
    """
    t = term.strip()
    if not t:
        return ""
    if source_lang.lower().startswith("en"):
        return f"I saw a {t} today."
    # Generic fallback
    return f"{t}."