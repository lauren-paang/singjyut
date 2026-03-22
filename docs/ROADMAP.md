# SingJyut 聲粵 — Roadmap

## Phase 1: Project Setup & Docs ✅
- [x] GitHub repo with MIT license
- [x] .gitignore, .env.example
- [x] PRD, SDD, Tech Spec, Roadmap
- [x] README.md

## Phase 2: Backend Core ✅
- [x] FastAPI server with all API endpoints
- [x] ToJyutping wrapper (`lib/jyutping.py`)
- [x] LRC parser (`lib/lyrics.py`)
- [x] syncedlyrics integration
- [x] Google Cloud TTS proxy (`lib/tts.py`)
- [x] YouTube Data API v3 search proxy

## Phase 3: Frontend Shell (Mobile-First) ✅
- [x] `index.html` — responsive layout
- [x] Search → results → song page flow
- [x] Jyutping above each character (char-block rendering)
- [x] Google Fonts (Inter + Noto Sans TC + Noto Serif TC)
- [x] `manifest.json` for PWA

## Phase 4: YouTube + Karaoke Sync ✅
- [x] YouTube IFrame API integration
- [x] KaraokeEngine: poll `getCurrentTime()`, highlight active line
- [x] Auto-scroll to active line
- [x] Tap lyric line to seek video to that timestamp

## Phase 5: TTS Integration ✅
- [x] Tap character → TTS single character
- [x] Tap 🔊 → TTS whole line
- [x] Client-side TTS audio cache

## Phase 6: Deployment ✅
- [x] Dockerfile
- [x] Deploy to Render free tier
- [x] Verify public URL on phone
- [x] PWA "Add to Home Screen" verification

## Phase 7: Polish ✅
- [x] Manual lyrics paste fallback
- [x] Loading states & error handling
- [x] Multi-strategy lyrics search (extracted title, user query, full YouTube title)
- [x] YouTube music category filter (videoCategoryId: 10)

## Phase 8: Frontend Redesign ✅
- [x] Light cream theme (#F5F0E8) with terracotta accent (#C4654A)
- [x] Removed mode toggle (Learn/Sing Along) — unified interaction
- [x] Fixed bottom playback bar with SVG icons (play/pause, prev/next line, progress bar)
- [x] Featured popular songs on homepage (8 classic Cantonese songs)
- [x] Font update to Inter + Noto Sans TC + Noto Serif TC
- [x] Desktop layout (600px max-width, responsive video)
- [x] Mobile optimizations (iOS auto-zoom fix, touch targets, small screen support)

---

## Known Issues

- [ ] YouTube video shows "Video unavailable" on mobile (works on desktop) — likely iOS security restriction on HTTP embeds, needs HTTPS or further investigation

---

## Future (Post-MVP)

- Database for persistent storage
- User accounts (login/signup)
- Save songs, sentences, characters
- History saving
- Tone coloring (color by tone number)
- Practice history / streak tracking
- Speed control
- Offline mode (cache lyrics + TTS)
- UniApp migration — cross-platform framework for mobile app + web from single codebase
- Apple Music / Spotify integration
