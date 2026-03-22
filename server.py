import os

from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

from lib.jyutping import annotate
from lib.lyrics import fetch_lyrics, search_lyrics, parse_manual_lyrics
from lib.tts import synthesize

app = FastAPI(title="SingJyut 聲粵")


# ── No-Cache Middleware (dev) ───────────────────────────────────────────────

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/public/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

app.add_middleware(NoCacheMiddleware)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")


# ── Request Models ──────────────────────────────────────────────────────────


class LyricsRequest(BaseModel):
    title: str
    artist: str = ""


class JyutpingRequest(BaseModel):
    text: str


class TTSRequest(BaseModel):
    text: str
    voice: str = "yue-HK-Standard-A"


class ManualLyricsRequest(BaseModel):
    text: str


# ── API Routes ──────────────────────────────────────────────────────────────


@app.get("/api/youtube/search")
async def youtube_search(q: str = Query(..., min_length=1)):
    """Search YouTube via Data API v3."""
    if not YOUTUBE_API_KEY:
        return {"results": [], "error": "YouTube API key not configured"}

    params = {
        "part": "snippet",
        "q": q,
        "type": "video",
        "videoCategoryId": "10",  # Music category
        "maxResults": 15,
        "key": YOUTUBE_API_KEY,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params,
            timeout=10,
        )
        if resp.status_code != 200:
            return {"results": [], "error": f"YouTube API error: {resp.status_code}"}

        data = resp.json()
        results = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            results.append({
                "videoId": item["id"]["videoId"],
                "title": snippet.get("title", ""),
                "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                "channelTitle": snippet.get("channelTitle", ""),
            })
        return {"results": results}


@app.post("/api/lyrics/search")
async def lyrics_search(req: LyricsRequest):
    """Check if synced lyrics are available."""
    return search_lyrics(req.title, req.artist)


@app.post("/api/lyrics/fetch")
async def lyrics_fetch(req: LyricsRequest):
    """Fetch lyrics with Jyutping annotation."""
    return fetch_lyrics(req.title, req.artist)


@app.post("/api/jyutping")
async def jyutping_convert(req: JyutpingRequest):
    """Convert text to Jyutping."""
    return {"chars": annotate(req.text)}


@app.post("/api/tts")
async def tts_generate(req: TTSRequest):
    """Generate Cantonese TTS audio."""
    audio = await synthesize(req.text, req.voice)
    if audio is None:
        return {"audio": None, "error": "TTS unavailable — check GOOGLE_TTS_KEY"}
    return {"audio": audio}


@app.post("/api/lyrics/manual")
async def lyrics_manual(req: ManualLyricsRequest):
    """Parse manually pasted lyrics with Jyutping annotation."""
    return parse_manual_lyrics(req.text)


# ── Static Files & SPA Fallback ─────────────────────────────────────────────

app.mount("/public", StaticFiles(directory="public"), name="public")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve index.html for all non-API routes (SPA fallback)."""
    return FileResponse("public/index.html")
