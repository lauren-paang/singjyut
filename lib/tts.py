import hashlib
import logging

import httpx

from lib import cache, config

logger = logging.getLogger(__name__)

TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
DEFAULT_VOICE = "yue-HK-Standard-A"


def is_configured() -> bool:
    return bool(config.GOOGLE_TTS_KEY)


def _cache_file(text: str, voice: str):
    digest = hashlib.sha256(f"{voice}|{text}".encode()).hexdigest()
    return config.DATA_DIR / "tts_cache" / f"{digest}.b64"


async def synthesize(text: str, voice: str = DEFAULT_VOICE) -> str | None:
    """Call Google Cloud TTS and return base64-encoded audio.

    Results are cached on disk (keyed by voice + text) to save API quota.
    Returns None when the key is missing or the API call fails.
    """
    if not is_configured():
        return None

    cache_file = _cache_file(text, voice)
    cached = cache.read_text(cache_file)
    if cached:
        return cached

    payload = {
        "input": {"text": text},
        "voice": {
            "languageCode": "yue-HK",
            "name": voice,
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 0.9,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
            resp = await client.post(
                TTS_URL,
                params={"key": config.GOOGLE_TTS_KEY},
                json=payload,
            )
    except httpx.HTTPError as exc:
        logger.warning("TTS request failed: %s", exc)
        return None

    if resp.status_code != 200:
        logger.warning("TTS API returned %s: %s", resp.status_code, resp.text[:200])
        return None

    try:
        audio = resp.json().get("audioContent")
    except ValueError:
        logger.warning("TTS API returned invalid JSON")
        return None
    if audio:
        cache.write_text(cache_file, audio)
    return audio
