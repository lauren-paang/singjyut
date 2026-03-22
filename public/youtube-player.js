// ── YouTube Player Module ────────────────────────────────────────────────────
// Wraps YouTube IFrame API with state management.

const YTPlayer = (() => {
    let player = null;
    let ready = false;
    let onStateChangeCb = null;

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
    };

    function loadVideo(videoId) {
        if (player) {
            player.loadVideoById(videoId);
            return;
        }

        if (!ready) {
            const check = setInterval(() => {
                if (ready) {
                    clearInterval(check);
                    createPlayer(videoId);
                }
            }, 100);
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
            },
            events: {
                onReady: (e) => {
                    console.log('[YTPlayer] ready');
                },
                onStateChange: (e) => {
                    if (onStateChangeCb) onStateChangeCb(e.data);
                },
                onError: (e) => {
                    console.error('[YTPlayer] error code:', e.data);
                    // 2=invalid param, 5=HTML5 error, 100=not found, 101/150=embed blocked
                },
            },
        });
    }

    function getCurrentTime() {
        if (player && typeof player.getCurrentTime === 'function') {
            return player.getCurrentTime();
        }
        return 0;
    }

    function getDuration() {
        if (player && typeof player.getDuration === 'function') {
            return player.getDuration();
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

    function onStateChange(cb) {
        onStateChangeCb = cb;
    }

    function seekTo(seconds) {
        if (player && typeof player.seekTo === 'function') {
            player.seekTo(seconds, true);
            player.playVideo();
        }
    }

    return { init, loadVideo, getCurrentTime, getDuration, isPlaying, play, pause, seekTo, onStateChange };
})();

YTPlayer.init();
