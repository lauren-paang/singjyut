# SingJyut 聲粵 — Technical Specification

## 1. Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | FastAPI (Python 3.11+) | Direct access to ToJyutping + syncedlyrics Python libraries |
| Jyutping | ToJyutping 3.2.0 | 99% accuracy, returns char-aligned `(char, jyutping)` tuples |
| Lyrics | syncedlyrics 1.0.1 | Fetches time-stamped LRC from Musixmatch/NetEase/Lrclib |
| TTS | Google Cloud TTS API | `yue-HK-Standard-A` voice for Cantonese |
| Music | YouTube IFrame API | Free embed, `getCurrentTime()` for karaoke sync |
| Search | YouTube Data API v3 | In-app search with music category filter (videoCategoryId: 10), 10K quota units/day free |
| Frontend | Vanilla JS + HTML + CSS | No build step, mobile-first, fast load |
| Fonts | Inter + Noto Sans TC + Noto Serif TC (Google Fonts) | Inter for UI, Noto Sans TC for Chinese body text, Noto Serif TC for lyric display |
| Theme | Light cream (#F5F0E8) + terracotta (#C4654A) | Warm, readable light theme |
| Deployment | Render free tier | Auto-deploy from GitHub, public URL |

## 2. API Specification

### GET /api/health

Liveness check. Reports which API keys are configured.

**Response:**
```json
{"status": "ok", "youtube": true, "tts": true}
```

### GET /api/youtube/search

Search YouTube for videos (filtered to music category).

**Query Parameters:**
- `q` (string, required) — Search query

**Response:**
```json
{
  "results": [
    {
      "videoId": "qu0S3MsFGBc",
      "title": "Beyond - 海闊天空",
      "thumbnail": "https://i.ytimg.com/vi/qu0S3MsFGBc/mqdefault.jpg",
      "channelTitle": "Beyond Official"
    }
  ]
}
```

### POST /api/lyrics/search

Check lyrics availability for a song.

**Request:**
```json
{
  "title": "海闊天空",
  "artist": "Beyond"
}
```

**Response:**
```json
{
  "found": true,
  "synced": true,
  "source": "musixmatch"
}
```

### POST /api/lyrics/fetch

Fetch lyrics with Jyutping annotation. Uses multi-strategy search (extracted title, user query, full YouTube title).

**Request:**
```json
{
  "title": "海闊天空",
  "artist": "Beyond"
}
```

**Response:**
```json
{
  "title": "海闊天空",
  "artist": "Beyond",
  "synced": true,
  "lines": [
    {
      "time": 32.5,
      "text": "今天我",
      "chars": [
        {"char": "今", "jyutping": "gam1"},
        {"char": "天", "jyutping": "tin1"},
        {"char": "我", "jyutping": "ngo5"}
      ]
    }
  ]
}
```

### POST /api/jyutping

Convert text to Jyutping.

**Request:**
```json
{
  "text": "你好世界"
}
```

**Response:**
```json
{
  "chars": [
    {"char": "你", "jyutping": "nei5"},
    {"char": "好", "jyutping": "hou2"},
    {"char": "世", "jyutping": "sai3"},
    {"char": "界", "jyutping": "gaai3"}
  ]
}
```

### POST /api/tts

Generate Cantonese TTS audio.

**Request:**
```json
{
  "text": "你好",
  "voice": "yue-HK-Standard-A"
}
```

**Response:**
```json
{
  "audio": "<base64-encoded-mp3>"
}
```

`text` is limited to 200 characters and `voice` must be a `yue-HK-*` voice.
On failure the response is `{"audio": null, "error": "..."}`.

### POST /api/lyrics/manual

Annotate pasted lyrics. Plain text gives unsynced lines (`"time": null`);
pasted LRC keeps its timestamps.

**Request:**
```json
{
  "text": "今天我\n寒冷的站在"
}
```

**Response:** same shape as `/api/lyrics/fetch`, with `"title": "Manual Lyrics"`.

## 3. LRC Format Parsing

Time-stamped LRC format: `[mm:ss.xx]lyrics text`

```
[00:32.50]今天我寒冷的站在
[00:37.20]飄過的是你的那一瞥
```

Accepted timestamps: `[mm:ss.xx]`, `[mm:ss.xxx]`, `[m:ss]`, `[mm:ss:xx]`.
A line may carry several timestamps (`[00:20.00][01:30.00]副歌`, a repeated
chorus) and yields one entry per timestamp; entries are sorted by time.
Word-level `<mm:ss.xx>` tags and metadata lines (`[ar:...]`) are dropped.

Time calculation: `minutes * 60 + seconds + fraction`, where the fraction digits
are read as a decimal (`.5` = 0.5s, `.50` = 0.5s, `.500` = 0.5s).

If a provider only has plain (unsynced) lyrics, each non-empty line becomes an
entry with `"time": null` and the response has `"synced": false`.

## 4. Karaoke Sync Algorithm

```javascript
// Poll every 200ms
setInterval(() => {
  const currentTime = player.getCurrentTime();
  const activeIndex = lines.findLastIndex(l => l.time <= currentTime);
  highlightLine(activeIndex);
}, 200);
```

## 5. PWA Configuration

**manifest.json:**
- `display: "standalone"` — removes browser chrome
- `theme_color: "#F5F0E8"` — light cream theme
- `start_url: "/"` — launches to main page

**Service Worker:** Disabled during active development. Will be re-enabled for offline caching of static assets before production release.

## 6. Deployment

### Render (Primary)
1. Connect GitHub repo
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
4. Add environment variables: `GOOGLE_TTS_KEY`, `YOUTUBE_API_KEY`
5. Free tier: spins down after 15 min inactivity (~30s cold start)

### Docker (Alternative)

See the `Dockerfile`: `python:3.11-slim`, non-root user, listens on `$PORT`
(default 8000), `HEALTHCHECK` on `/api/health`. `.dockerignore` keeps `.env`,
caches and tests out of the image.
