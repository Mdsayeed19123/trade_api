"""
Configuration – all tuneable values live here.
Override any value by setting the corresponding environment variable.
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # ── Auth ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_super_secret_key_2024")
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    # ── Rate limiting ──────────────────────────────────────────────────────────
    RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "10"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # ── AI (Gemini) ────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # ── Web search (DuckDuckGo – no key required) ──────────────────────────────
    SEARCH_MAX_RESULTS: int = int(os.getenv("SEARCH_MAX_RESULTS", "8"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))


settings = Settings()
