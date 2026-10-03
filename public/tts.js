// ── TTS Module ──────────────────────────────────────────────────────────────
// Handles text-to-speech for Cantonese characters and lines.

const TTS = (() => {
    const cache = new Map();
    let currentAudio = null;
    let requestSeq = 0;   // only the most recent tap may play

    async function speak(text) {
        if (!text || !text.trim()) return;

        stop();
        const seq = ++requestSeq;

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
                // A newer tap arrived while this one was loading.
                if (seq !== requestSeq) return;
                return playBase64(data.audio);
            }
            if (data.error) console.warn('TTS:', data.error);
        } catch (err) {
            console.warn('TTS error:', err);
        }
    }

    function playBase64(b64) {
        return new Promise((resolve) => {
            const audio = new Audio(`data:audio/mpeg;base64,${b64}`);
            currentAudio = audio;
            audio.onended = () => {
                if (currentAudio === audio) currentAudio = null;
                resolve();
            };
            audio.onerror = () => {
                if (currentAudio === audio) currentAudio = null;
                resolve();
            };
            audio.play().catch(() => resolve());
        });
    }

    function stop() {
        requestSeq++;
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
    }

    return { speak, stop };
})();
