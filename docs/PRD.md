# SingJyut 聲粵 — Product Requirements Document

## 1. Overview

SingJyut is a mobile-first PWA that helps users learn Cantonese through songs. It layers Jyutping pronunciation annotations, text-to-speech, and karaoke-style lyric highlighting on top of YouTube music videos.

## 2. Problem Statement

Learning Cantonese songs is difficult because:
- Music apps display lyrics but never show Jyutping (pronunciation romanization)
- No existing tool combines music playback with character-level pronunciation
- Cantonese learners want to practice during 碎片时间 (fragmented time) on their phones

## 3. Target Users

- Cantonese language learners (beginner to intermediate)
- Users who enjoy learning languages through music
- Heritage speakers who can speak but want to read/write better

## 4. MVP Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | Song Search | YouTube search with music category filter (videoCategoryId: 10) |
| 2 | Jyutping Annotation | Jyutping romanization above every Chinese character |
| 3 | Karaoke Sync | Active lyric line highlighted with soft highlighter effect, auto-scroll |
| 4 | TTS Read-Aloud | Tap any character or 🔊 button to hear Cantonese pronunciation |
| 5 | YouTube Mini-Player | Embedded player that shrinks to top-right corner when scrolling lyrics |
| 6 | Playback Bar | Fixed bottom bar with play/pause, prev/next line, progress bar, time display |
| 7 | Tap-to-Seek | Tap any lyric line to jump the video to that timestamp |
| 8 | Multi-Strategy Lyrics Search | Tries extracted title, user query, and full YouTube title |
| 9 | Manual Lyrics Paste | Fallback when automatic lyrics search fails |
| 10 | Featured Songs | Popular Cantonese songs on the homepage for quick access |
| 11 | Mobile-First PWA | Installable on home screen, responsive design |
| 12 | Public Deployment | Accessible via phone over internet (Render free tier) |

## 5. Copyright Model

YouTube embed model (same as LingoClip, 10M+ users):
- YouTube handles all music licensing via Content ID
- The app adds a **learning layer** (Jyutping + TTS) — no music is hosted or downloaded
- If a video is on YouTube and embeddable, it's safe to embed

## 6. Success Metrics

- App loads and is usable on mobile phone via public URL
- Search returns relevant YouTube results
- Jyutping appears correctly above characters (99%+ accuracy via ToJyutping)
- Karaoke sync highlights the correct line during playback
- TTS plays correct Cantonese pronunciation for tapped characters

## 7. Future Features (Post-MVP)

- Database for persistent storage
- User accounts (login/signup)
- Save songs, sentences, and individual characters
- Tone coloring (color-code by tone number)
- Practice history / streak tracking
- Speed control for YouTube playback
- Offline mode
- Native iOS app (Capacitor or SwiftUI)
