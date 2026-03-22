# SingJyut 聲粵 — System Design Document

## 1. Architecture Overview

```
Mobile Browser / PWA
  │
  ├── GET  /api/youtube/search  → YouTube Data API v3 proxy
  ├── POST /api/lyrics/search   → syncedlyrics search
  ├── POST /api/lyrics/fetch    → fetch LRC + annotate with Jyutping
  ├── POST /api/tts             → Google Cloud TTS proxy (yue-HK)
  ├── POST /api/jyutping        → text → Jyutping conversion
  │
FastAPI (Python)
  ├── ToJyutping                → character → Jyutping mapping
  ├── syncedlyrics              → time-stamped LRC lyrics
  └── Google Cloud TTS          → Cantonese pronunciation
```

## 2. Component Design

### 2.1 Backend (FastAPI)

**`server.py`** — Single-file FastAPI application serving both API and static files.

**`lib/jyutping.py`** — Wraps ToJyutping to return `[{"char": "海", "jyutping": "hoi2"}]` tuples.

**`lib/lyrics.py`** — Fetches time-stamped LRC lyrics via syncedlyrics, parses `[mm:ss.xx]text` format, and combines with Jyutping annotation. Supports multi-strategy search (extracted title, user query, full YouTube title).

**`lib/tts.py`** — Proxies requests to Google Cloud TTS API with `yue-HK` voice configuration.

### 2.2 Frontend (Vanilla JS)

**`public/app.js`** — Main application logic: search, results display, song page rendering with Jyutping above characters, playback bar controls (play/pause, prev/next line, progress bar, time display), and mini-player behavior.

**`public/youtube-player.js`** — YouTube IFrame API wrapper with `getDuration()`, `seekTo()`, and playback state management. Supports mini-player mode (video shrinks to top-right corner via IntersectionObserver when user scrolls into lyrics).

**`public/karaoke.js`** — KaraokeEngine that polls `getCurrentTime()` and highlights the active lyric line with a soft highlighter effect and auto-scroll.

**`public/tts.js`** — TTS client: character tap → API call → audio playback, with client-side caching.

### 2.3 Data Flow

```
Search Flow:
  User types query → GET /api/youtube/search → YouTube API (videoCategoryId: 10) → results list

Song Load Flow:
  User taps result → POST /api/lyrics/fetch (title + artist)
                   → Multi-strategy lyrics search (extracted title → user query → full title)
                   → syncedlyrics fetches LRC
                   → ToJyutping annotates each character
                   → Returns {lines: [{time, chars: [{char, jyutping}]}]}

Karaoke Flow:
  YouTube plays → JS polls getCurrentTime() every 200ms
               → Compare against LRC timestamps
               → Highlight active line with soft highlighter, auto-scroll

Playback Bar Flow:
  Play/Pause → toggles YouTube player state
  Prev/Next  → seeks to previous/next lyric line timestamp
  Progress   → syncs with YouTube currentTime, tap to seek
  Lyric tap  → seeks video to that line's timestamp

Mini-Player Flow:
  IntersectionObserver watches video container
  → When video scrolls out of view, shrink to fixed top-right mini-player
  → When scrolled back into view, restore to full size

TTS Flow:
  User taps char → POST /api/tts {text, voice}
                 → Google Cloud TTS → base64 audio
                 → Browser plays audio (cached in memory)
```

## 3. Security

- All API keys stay server-side (proxied through FastAPI)
- `.env` is gitignored — keys set via deployment platform dashboard
- No user data collected in MVP (no database)
- CORS configured for same-origin only in production

## 4. Caching Strategy

- **Lyrics cache**: Server-side file cache in `data/lyrics_cache/` (by song hash)
- **TTS cache**: Client-side in-memory Map (per session)
- **Jyutping**: No cache needed — ToJyutping runs in-process, ~1ms per line

## 5. Performance Targets

- Search results: < 2s
- Lyrics + Jyutping load: < 3s
- TTS response: < 500ms
- Karaoke sync accuracy: ±200ms
