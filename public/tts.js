// ── TTS Module ──────────────────────────────────────────────────────────────
// Handles text-to-speech for Cantonese characters and lines.

const TTS = (() => {
    const cache = new Map();
    let currentAudio = null;

    async function speak(text) {
        if (!text || !text.trim()) return;

        // Stop any currently playing audio
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }

        // Check cache
        if (cache.has(text)) {
            return playBase64(cache.get(text));
        }

        try {
            const resp = await fetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            const data = await resp.json();
            if (data.audio) {
                cache.set(text, data.audio);
                return playBase64(data.audio);
            }
        } catch (err) {
            console.warn('TTS error:', err);
        }
    }

    function playBase64(b64) {
        return new Promise((resolve) => {
            const audio = new Audio(`data:audio/mp3;base64,${b64}`);
            currentAudio = audio;
            audio.onended = () => {
                currentAudio = null;
                resolve();
            };
            audio.onerror = () => {
                currentAudio = null;
                resolve();
            };
            audio.play().catch(() => resolve());
        });
    }

    function stop() {
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
    }

    return { speak, stop };
})();
