// ── YouTube Player Module ────────────────────────────────────────────────────
// Wraps YouTube IFrame API with state management.

const YTPlayer = (() => {
    let player = null;
    let ready = false;
    let pendingVideoId = null;   // requested before the API finished loading
    let onStateChangeCb = null;
    let onErrorCb = null;

    function init() {
        if (window.YT && window.YT.Player) {
            ready = true;
            return;
        }
        const tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        document.head.appendChild(tag);
    }

    window.onYouTubeIframeAPIReady = () => {
        ready = true;
        if (pendingVideoId && !player) {
            createPlayer(pendingVideoId);
            pendingVideoId = null;
        }
    };

    function loadVideo(videoId) {
        if (player) {
            player.loadVideoById(videoId);
            return;
        }

        if (!ready) {
            // Only the latest request matters; onYouTubeIframeAPIReady picks it up.
            pendingVideoId = videoId;
            return;
        }

        createPlayer(videoId);
    }

    function createPlayer(videoId) {
        player = new YT.Player('youtube-player', {
            videoId,
            playerVars: {
                playsinline: 1,
                rel: 0,
                fs: 0,
                origin: window.location.origin,
            },
            events: {
                onReady: () => {
                    console.log('[YTPlayer] ready');
                },
                onStateChange: (e) => {
                    if (onStateChangeCb) onStateChangeCb(e.data);
                },
                onError: (e) => {
                    // 2=invalid param, 5=HTML5 error, 100=not found, 101/150=embed blocked
                    console.error('[YTPlayer] error code:', e.data);
                    if (onErrorCb) onErrorCb(e.data);
                },
            },
        });
    }

    function getCurrentTime() {
        if (player && typeof player.getCurrentTime === 'function') {
            return player.getCurrentTime() || 0;
        }
        return 0;
    }

    function getDuration() {
        if (player && typeof player.getDuration === 'function') {
            return player.getDuration() || 0;
        }
        return 0;
    }

    function isPlaying() {
        if (player && typeof player.getPlayerState === 'function') {
            return player.getPlayerState() === YT.PlayerState.PLAYING;
        }
        return false;
    }

    function play() {
        if (player && typeof player.playVideo === 'function') {
            player.playVideo();
        }
    }

    function pause() {
        if (player && typeof player.pauseVideo === 'function') {
            player.pauseVideo();
        }
    }

    // Leaving the song view: stop playback and drop a video still waiting
    // for the API to load.
    function stop() {
        pendingVideoId = null;
        pause();
    }

    function onStateChange(cb) {
        onStateChangeCb = cb;
    }

    function onError(cb) {
        onErrorCb = cb;
    }

    function seekTo(seconds) {
        if (player && typeof player.seekTo === 'function') {
            player.seekTo(seconds, true);
            player.playVideo();
        }
    }

    return { init, loadVideo, getCurrentTime, getDuration, isPlaying, play, pause, stop, seekTo, onStateChange, onError };
})();

YTPlayer.init();
