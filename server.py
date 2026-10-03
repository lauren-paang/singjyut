import html

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from lib import config
from lib import tts
from lib.jyutping import annotate
from lib.lyrics import fetch_lyrics, search_lyrics, parse_manual_lyrics

app = FastAPI(title="SingJyut 聲粵")


# ── Cache-Control Middleware ────────────────────────────────────────────────

class RevalidateStaticMiddleware(BaseHTTPMiddleware):
    """Make browsers revalidate the app shell so deploys show up immediately.

    `no-cache` still allows ETag-based 304s for /public/ assets, unlike the
    previous `no-store`.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-cache")
        return response

app.add_middleware(RevalidateStaticMiddleware)


# ── Request Models ──────────────────────────────────────────────────────────


class LyricsRequest(BaseModel):
    title: str = Field(..., max_length=300)
    artist: str = Field("", max_length=300)


class JyutpingRequest(BaseModel):
    text: str = Field(..., max_length=5000)


class TTSRequest(BaseModel):
    # Capped to keep a public deployment from burning the TTS quota.
    text: str = Field(..., min_length=1, max_length=200)
    voice: str = Field(tts.DEFAULT_VOICE, pattern=r"^yue-HK-[A-Za-z0-9-]+$", max_length=64)


class ManualLyricsRequest(BaseModel):
    text: str = Field(..., max_length=20000)


# ── API Routes ──────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    """Liveness check; also reports which API keys are configured."""
    return {
        "status": "ok",
        "youtube": bool(config.YOUTUBE_API_KEY),
        "tts": tts.is_configured(),
    }


@app.get("/api/youtube/search")
async def youtube_search(q: str = Query(..., min_length=1, max_length=200)):
    """Search YouTube via Data API v3."""
    if not config.YOUTUBE_API_KEY:
        return {"results": [], "error": "YouTube API key not configured"}

    params = {
        "part": "snippet",
        "q": q,
        "type": "video",
        "videoCategoryId": "10",  # Music category
        "maxResults": 15,
        "key": config.YOUTUBE_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
            )
    except httpx.HTTPError:
        return {"results": [], "error": "YouTube search is unreachable, please try again"}

    if resp.status_code != 200:
        return {"results": [], "error": f"YouTube API error: {resp.status_code}"}

    data = resp.json()
    results = []
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue
        snippet = item.get("snippet", {})
        thumbnails = snippet.get("thumbnails", {})
        thumbnail = next(
            (thumbnails[size]["url"] for size in ("medium", "high", "default")
             if thumbnails.get(size, {}).get("url")),
            "",
        )
        results.append({
            "videoId": video_id,
            # The Data API returns HTML-escaped text (e.g. "Don&#39;t").
            "title": html.unescape(snippet.get("title", "")),
            "thumbnail": thumbnail,
            "channelTitle": html.unescape(snippet.get("channelTitle", "")),
        })
    return {"results": results}


# Lyrics/Jyutping routes are plain `def`: syncedlyrics does blocking network
# I/O, so FastAPI must run them in its threadpool, not on the event loop.

@app.post("/api/lyrics/search")
def lyrics_search(req: LyricsRequest):
    """Check if synced lyrics are available."""
    return search_lyrics(req.title, req.artist)


@app.post("/api/lyrics/fetch")
def lyrics_fetch(req: LyricsRequest):
    """Fetch lyrics with Jyutping annotation."""
    return fetch_lyrics(req.title, req.artist)


@app.post("/api/jyutping")
def jyutping_convert(req: JyutpingRequest):
    """Convert text to Jyutping."""
    return {"chars": annotate(req.text)}


@app.post("/api/tts")
async def tts_generate(req: TTSRequest):
    """Generate Cantonese TTS audio."""
    if not tts.is_configured():
        return {"audio": None, "error": "TTS unavailable — check GOOGLE_TTS_KEY"}
    audio = await tts.synthesize(req.text, req.voice)
    if audio is None:
        return {"audio": None, "error": "TTS request failed, please try again"}
    return {"audio": audio}


@app.post("/api/lyrics/manual")
def lyrics_manual(req: ManualLyricsRequest):
    """Parse manually pasted lyrics with Jyutping annotation."""
    return parse_manual_lyrics(req.text)


# ── Static Files & SPA Fallback ─────────────────────────────────────────────

app.mount("/public", StaticFiles(directory=config.PUBLIC_DIR), name="public")


@app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
async def serve_spa(full_path: str):
    """Serve index.html for all non-API routes (SPA fallback)."""
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(config.PUBLIC_DIR / "index.html")
