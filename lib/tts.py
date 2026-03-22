import os
import httpx

GOOGLE_TTS_KEY = os.getenv("GOOGLE_TTS_KEY", "")
TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


async def synthesize(text: str, voice: str = "yue-HK-Standard-A") -> str | None:
    """Call Google Cloud TTS and return base64-encoded audio."""
    if not GOOGLE_TTS_KEY:
        return None

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

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TTS_URL}?key={GOOGLE_TTS_KEY}",
            json=payload,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("audioContent")
        return None
