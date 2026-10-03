"""Runtime configuration, read from environment variables (and `.env`).

Modules read these attributes at call time (`config.X`), so tests can
monkeypatch them without reloading anything.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"

load_dotenv(BASE_DIR / ".env")


def _secret(name: str) -> str:
    """Read an API key, treating the `.env.example` placeholders as unset."""
    value = os.getenv(name, "").strip()
    if value.startswith("your_"):
        return ""
    return value


YOUTUBE_API_KEY = _secret("YOUTUBE_API_KEY")
GOOGLE_TTS_KEY = _secret("GOOGLE_TTS_KEY")

# Writable directory for the lyrics and TTS caches.
DATA_DIR = Path(os.getenv("DATA_DIR") or BASE_DIR / "data")

# Timeout (seconds) for outbound calls to Google APIs.
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10"))
