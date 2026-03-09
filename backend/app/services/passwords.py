import re


def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter")

    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")