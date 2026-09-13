// Smart AI Studio Web - Core Application Logic (Optimized)

let currentVideoPath = "";
let currentVideoUrl = "";
let subtitles = [];
let downloadedSeriesList = [];
let selectedLogoPath = "";
let logoImage = null;
let currentSubtitleRow = -1;

let taskTimerInterval = null;
let taskStartTime = 0;

// Session ID for temp files isolation
const sessionId = "session_" + Math.random().toString(36).substring(2, 9);

// Canvas & Overlay State
const canvasState = {
    // Title
    titleText: "",
    titleNormX: 0.35,
    titleNormY: 0.08,
    titleColor: "#FFEA00",
    titleFontFamily: "Battambang",
    titleFontSize: 26,
    titleRect: null,
    titleHandleRect: null,

    // Subtitle
    subText: "",
    subNormY: 0.85,
    subColor: "#FFFFFF",
    subFontFamily: "Battambang",
    subFontSize: 18,
    subRect: null,
    subHandleRect: null,
    showSubtitles: true,

    // Logo
    logoNormX: 0.85,
    logoNormY: 0.05,
    logoNormW: 0.15,
    logoRect: null,
    logoHandleRect: null,

    // Blur Ellipse
    enableBlur: false,
    blurNormX: 0.05,
    blurNormY: 0.05,
    blurNormW: 0.18,
    blurNormH: 0.12,
    blurStrength: 25,
    blurTint: "#FFFFFF",
    blurTintOpacity: 0,
    blurRect: null,
    blurHandleSE: null,
    blurHandleE: null,
    blurHandleS: null,

    // Drag / Resize tracking
    activeMode: null,
    dragOffset: { x: 0, y: 0 },
    resizeStartPos: { x: 0, y: 0 },
    initialFontSize: 26,
    initialSubFontSize: 18,
    initialLogoNormW: 0.15,
    initialBlurNormW: 0.18,
    initialBlurNormH: 0.12
};

// DOM Elements
const video = document.getElementById("main-video");
const canvas = document.getElementById("overlay-canvas");
const ctx = canvas.getContext("2d");
const ttsAudioPlayer = document.getElementById("tts-audio-player");

const btnPlayPause = document.getElementById("btn-play-pause");
const btnStop = document.getElementById("btn-stop");
const btnMuteOrig = document.getElementById("btn-mute-orig");
const btnMuteTts = document.getElementById("btn-mute-tts");
const videoSeekSlider = document.getElementById("video-seek-slider");
const timeDisplay = document.getElementById("time-display");
const selectEpisode = document.getElementById("select-episode");

const progressBarFill = document.getElementById("progress-bar-fill");
const taskStatusLabel = document.getElementById("task-status-label");
const taskTimerLabel = document.getElementById("task-timer-label");
const taskProgressPercent = document.getElementById("task-progress-percent");

// Initialize Canvas Size
function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

// Stopwatch Helpers
function formatElapsed(sec) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    return `⏱️ ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function startTimer() {
    clearInterval(taskTimerInterval);
    taskStartTime = Date.now();
    taskTimerLabel.innerText = "⏱️ 00:00:00";
    taskTimerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - taskStartTime) / 1000);
        taskTimerLabel.innerText = formatElapsed(elapsed);
    }, 1000);
}

function stopTimer() {
    clearInterval(taskTimerInterval);
}

// ================= TRANSPARENT OVERLAY RENDER LOOP (HARDWARE ACCELERATED) =================
function renderCanvas() {
    if (canvas.width <= 0 || canvas.height <= 0) {
        requestAnimationFrame(renderCanvas);
        return;
    }

    // Clear transparent overlay
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Compute actual video display rect within canvas (object-fit: contain geometry)
    let vx = 0, vy = 0, vw = canvas.width, vh = canvas.height;
    if (video.videoWidth > 0 && video.videoHeight > 0) {
        const scale = Math.min(canvas.width / video.videoWidth, canvas.height / video.videoHeight);
        vw = Math.floor(video.videoWidth * scale);
        vh = Math.floor(video.videoHeight * scale);
        vx = Math.floor((canvas.width - vw) / 2);
        vy = Math.floor((canvas.height - vh) / 2);
    }

    // 1. Draw Circle / Ellipse Blur Overlay
    if (canvasState.enableBlur) {
        const bx = Math.floor(vx + canvasState.blurNormX * vw);
        const by = Math.floor(vy + canvasState.blurNormY * vh);
        const bw = Math.max(20, Math.floor(canvasState.blurNormW * vw));
        const bh = Math.max(15, Math.floor(canvasState.blurNormH * vh));

        canvasState.blurRect = { x: bx, y: by, w: bw, h: bh };

        ctx.save();
        ctx.beginPath();
        ctx.ellipse(bx + bw / 2, by + bh / 2, bw / 2, bh / 2, 0, 0, Math.PI * 2);
        
        // Frosted Blur Tint Fill
        if (canvasState.blurTintOpacity > 0) {
            ctx.fillStyle = canvasState.blurTint;
            ctx.globalAlpha = Math.max(0.2, canvasState.blurTintOpacity / 100.0);
            ctx.fill();
        } else {
            ctx.fillStyle = "rgba(20, 30, 45, 0.75)";
            ctx.fill();
        }
        ctx.restore();

        // Blur Ellipse outline
        ctx.strokeStyle = "#00F2FE";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.ellipse(bx + bw / 2, by + bh / 2, bw / 2, bh / 2, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        // Blur Handles
        canvasState.blurHandleSE = { x: bx + bw - 6, y: by + bh - 6, w: 10, h: 10 };
        canvasState.blurHandleE = { x: bx + bw - 4, y: by + bh / 2 - 4, w: 8, h: 8 };
        canvasState.blurHandleS = { x: bx + bw / 2 - 4, y: by + bh - 4, w: 8, h: 8 };

        ctx.fillStyle = "#00F2FE";
        ctx.fillRect(canvasState.blurHandleSE.x, canvasState.blurHandleSE.y, canvasState.blurHandleSE.w, canvasState.blurHandleSE.h);
        ctx.fillRect(canvasState.blurHandleE.x, canvasState.blurHandleE.y, canvasState.blurHandleE.w, canvasState.blurHandleE.h);
        ctx.fillRect(canvasState.blurHandleS.x, canvasState.blurHandleS.y, canvasState.blurHandleS.w, canvasState.blurHandleS.h);
    } else {
        canvasState.blurRect = null;
    }

    // 2. Draw Title
    if (canvasState.titleText.trim()) {
        ctx.font = `bold ${canvasState.titleFontSize}px '${canvasState.titleFontFamily}', sans-serif`;
        const metrics = ctx.measureText(canvasState.titleText);
        const tw = metrics.width;
        const th = canvasState.titleFontSize;

        const tx = Math.floor(vx + canvasState.titleNormX * vw);
        const ty = Math.floor(vy + canvasState.titleNormY * vh);

        canvasState.titleRect = { x: tx - 6, y: ty - th + 4, w: tw + 12, h: th + 8 };

        // Background box
        ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
        ctx.strokeStyle = "#00F2FE";
        ctx.setLineDash([3, 3]);
        ctx.strokeRect(canvasState.titleRect.x, canvasState.titleRect.y, canvasState.titleRect.w, canvasState.titleRect.h);
        ctx.setLineDash([]);

        // Text Shadow & Fill
        ctx.fillStyle = "#000000";
        for (let dx of [-2, 0, 2]) {
            for (let dy of [-2, 0, 2]) {
                ctx.fillText(canvasState.titleText, tx + dx, ty + dy);
            }
        }
        ctx.fillStyle = canvasState.titleColor;
        ctx.fillText(canvasState.titleText, tx, ty);

        // Title Resize Handle
        canvasState.titleHandleRect = { x: canvasState.titleRect.x + canvasState.titleRect.w - 6, y: canvasState.titleRect.y + canvasState.titleRect.h - 6, w: 8, h: 8 };
        ctx.fillStyle = "#00F2FE";
        ctx.fillRect(canvasState.titleHandleRect.x, canvasState.titleHandleRect.y, canvasState.titleHandleRect.w, canvasState.titleHandleRect.h);
    } else {
        canvasState.titleRect = null;
    }

    // 3. Draw Logo (Instant Fix)
    if (logoImage && logoImage.complete && logoImage.naturalWidth > 0) {
        const lw = Math.max(30, Math.floor(canvasState.logoNormW * vw));
        const lh = Math.floor(lw * (logoImage.naturalHeight / logoImage.naturalWidth));
        const lx = Math.floor(vx + canvasState.logoNormX * vw);
        const ly = Math.floor(vy + canvasState.logoNormY * vh);

        canvasState.logoRect = { x: lx - 4, y: ly - 4, w: lw + 8, h: lh + 8 };

        ctx.strokeStyle = "#FFEA00";
        ctx.setLineDash([3, 3]);
        ctx.strokeRect(canvasState.logoRect.x, canvasState.logoRect.y, canvasState.logoRect.w, canvasState.logoRect.h);
        ctx.setLineDash([]);

        ctx.drawImage(logoImage, lx, ly, lw, lh);

        canvasState.logoHandleRect = { x: canvasState.logoRect.x + canvasState.logoRect.w - 6, y: canvasState.logoRect.y + canvasState.logoRect.h - 6, w: 8, h: 8 };
        ctx.fillStyle = "#FFEA00";
        ctx.fillRect(canvasState.logoHandleRect.x, canvasState.logoHandleRect.y, canvasState.logoHandleRect.w, canvasState.logoHandleRect.h);
    } else {
        canvasState.logoRect = null;
    }

    // 4. Draw Subtitle (Checked via showSubtitles toggle)
    if (canvasState.showSubtitles && canvasState.subText.trim()) {
        ctx.font = `bold ${canvasState.subFontSize}px '${canvasState.subFontFamily}', sans-serif`;
        const metrics = ctx.measureText(canvasState.subText);
        const sw = metrics.width;
        const sh = canvasState.subFontSize;

        const rw = sw + 28;
        const rh = sh + 14;
        const rx = Math.floor(vx + 0.5 * vw) - Math.floor(rw / 2);
        const ry = Math.floor(vy + canvasState.subNormY * vh);

        canvasState.subRect = { x: rx, y: ry, w: rw, h: rh };

        // Subtitle background box
        ctx.fillStyle = "rgba(0, 0, 0, 0.75)";
        ctx.strokeStyle = "#00FF99";
        ctx.setLineDash([3, 3]);
        ctx.strokeRect(rx, ry, rw, rh);
        ctx.setLineDash([]);

        // Shadow & Text
        ctx.fillStyle = "#000000";
        for (let dx of [-2, 0, 2]) {
            for (let dy of [-2, 0, 2]) {
                ctx.fillText(canvasState.subText, rx + 14 + dx, ry + sh + dy - 2);
            }
        }
        ctx.fillStyle = canvasState.subColor;
        ctx.fillText(canvasState.subText, rx + 14, ry + sh - 2);

        canvasState.subHandleRect = { x: rx + rw - 6, y: ry + rh - 6, w: 8, h: 8 };
        ctx.fillStyle = "#00FF99";
        ctx.fillRect(canvasState.subHandleRect.x, canvasState.subHandleRect.y, canvasState.subHandleRect.w, canvasState.subHandleRect.h);
    } else {
        canvasState.subRect = null;
    }

    requestAnimationFrame(renderCanvas);
}
requestAnimationFrame(renderCanvas);

// ================= CANVAS INTERACTION (DRAG & RESIZE) =================
function isInside(pos, rect) {
    return rect && pos.x >= rect.x && pos.x <= rect.x + rect.w && pos.y >= rect.y && pos.y <= rect.y + rect.h;
}

function getCanvasPos(e) {
    const r = canvas.getBoundingClientRect();
    return {
        x: (e.clientX - r.left) * (canvas.width / r.width),
        y: (e.clientY - r.top) * (canvas.height / r.height)
    };
}

function getVideoRect() {
    let vx = 0, vy = 0, vw = canvas.width, vh = canvas.height;
    if (video.videoWidth > 0 && video.videoHeight > 0) {
        const scale = Math.min(canvas.width / video.videoWidth, canvas.height / video.videoHeight);
        vw = Math.floor(video.videoWidth * scale);
        vh = Math.floor(video.videoHeight * scale);
        vx = Math.floor((canvas.width - vw) / 2);
        vy = Math.floor((canvas.height - vh) / 2);
    }
    return { vx, vy, vw: Math.max(1, vw), vh: Math.max(1, vh) };
}

canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const pos = getCanvasPos(e);
    const delta = e.deltaY < 0 ? 1 : -1;

    if (canvasState.enableBlur && isInside(pos, canvasState.blurRect)) {
        const step = delta * 0.015;
        canvasState.blurNormW = Math.max(0.02, Math.min(0.95, canvasState.blurNormW + step));
        canvasState.blurNormH = Math.max(0.02, Math.min(0.95, canvasState.blurNormH + step));
        return;
    }

    if (isInside(pos, canvasState.subRect)) {
        canvasState.subFontSize = Math.max(10, Math.min(60, canvasState.subFontSize + delta * 2));
        document.getElementById("input-sub-size").value = canvasState.subFontSize;
        return;
    }

    if (isInside(pos, canvasState.titleRect)) {
        canvasState.titleFontSize = Math.max(12, Math.min(80, canvasState.titleFontSize + delta * 2));
        document.getElementById("input-title-size").value = canvasState.titleFontSize;
        return;
    }

    if (isInside(pos, canvasState.logoRect)) {
        const step = delta * 0.015;
        canvasState.logoNormW = Math.max(0.04, Math.min(0.60, canvasState.logoNormW + step));
        return;
    }
});

canvas.addEventListener("mousedown", (e) => {
    const pos = getCanvasPos(e);

    if (canvasState.enableBlur) {
        if (isInside(pos, canvasState.blurHandleSE)) {
            canvasState.activeMode = "resize_blur_se";
            canvasState.resizeStartPos = pos;
            canvasState.initialBlurNormW = canvasState.blurNormW;
            canvasState.initialBlurNormH = canvasState.blurNormH;
            return;
        }
        if (isInside(pos, canvasState.blurHandleE)) {
            canvasState.activeMode = "resize_blur_e";
            canvasState.resizeStartPos = pos;
            canvasState.initialBlurNormW = canvasState.blurNormW;
            return;
        }
        if (isInside(pos, canvasState.blurHandleS)) {
            canvasState.activeMode = "resize_blur_s";
            canvasState.resizeStartPos = pos;
            canvasState.initialBlurNormH = canvasState.blurNormH;
            return;
        }
    }

    if (isInside(pos, canvasState.titleHandleRect)) {
        canvasState.activeMode = "resize_title";
        canvasState.resizeStartPos = pos;
        canvasState.initialFontSize = canvasState.titleFontSize;
        return;
    }

    if (isInside(pos, canvasState.logoHandleRect)) {
        canvasState.activeMode = "resize_logo";
        canvasState.resizeStartPos = pos;
        canvasState.initialLogoNormW = canvasState.logoNormW;
        return;
    }

    if (isInside(pos, canvasState.subHandleRect)) {
        canvasState.activeMode = "resize_subtitle";
        canvasState.resizeStartPos = pos;
        canvasState.initialSubFontSize = canvasState.subFontSize;
        return;
    }

    // Drag detection
    if (canvasState.enableBlur && isInside(pos, canvasState.blurRect)) {
        canvasState.activeMode = "drag_blur";
        canvasState.dragOffset = { x: pos.x - canvasState.blurRect.x, y: pos.y - canvasState.blurRect.y };
    } else if (isInside(pos, canvasState.titleRect)) {
        canvasState.activeMode = "drag_title";
        canvasState.dragOffset = { x: pos.x - canvasState.titleRect.x, y: pos.y - canvasState.titleRect.y };
    } else if (isInside(pos, canvasState.logoRect)) {
        canvasState.activeMode = "drag_logo";
        canvasState.dragOffset = { x: pos.x - canvasState.logoRect.x, y: pos.y - canvasState.logoRect.y };
    } else if (isInside(pos, canvasState.subRect)) {
        canvasState.activeMode = "drag_subtitle";
        canvasState.dragOffset = { x: pos.x - canvasState.subRect.x, y: pos.y - canvasState.subRect.y };
    }
});

canvas.addEventListener("mousemove", (e) => {
    const pos = getCanvasPos(e);
    const { vx, vy, vw, vh } = getVideoRect();

    // Cursor Styling
    if (canvasState.enableBlur && isInside(pos, canvasState.blurHandleSE)) canvas.style.cursor = "se-resize";
    else if (canvasState.enableBlur && isInside(pos, canvasState.blurHandleE)) canvas.style.cursor = "e-resize";
    else if (canvasState.enableBlur && isInside(pos, canvasState.blurHandleS)) canvas.style.cursor = "s-resize";
    else if (isInside(pos, canvasState.titleHandleRect) || isInside(pos, canvasState.logoHandleRect) || isInside(pos, canvasState.subHandleRect)) canvas.style.cursor = "se-resize";
    else if ((canvasState.enableBlur && isInside(pos, canvasState.blurRect)) || isInside(pos, canvasState.titleRect) || isInside(pos, canvasState.logoRect) || isInside(pos, canvasState.subRect)) canvas.style.cursor = "move";
    else canvas.style.cursor = "default";

    if (!canvasState.activeMode) return;

    if (canvasState.activeMode === "drag_blur") {
        const nx = (pos.x - canvasState.dragOffset.x - vx) / vw;
        const ny = (pos.y - canvasState.dragOffset.y - vy) / vh;
        canvasState.blurNormX = Math.max(0.0, Math.min(0.95, nx));
        canvasState.blurNormY = Math.max(0.0, Math.min(0.95, ny));
    } else if (canvasState.activeMode === "drag_title") {
        const nx = (pos.x - canvasState.dragOffset.x - vx) / vw;
        const ny = (pos.y - canvasState.dragOffset.y - vy) / vh;
        canvasState.titleNormX = Math.max(0.0, Math.min(0.95, nx));
        canvasState.titleNormY = Math.max(0.0, Math.min(0.95, ny));
    } else if (canvasState.activeMode === "drag_logo") {
        const nx = (pos.x - canvasState.dragOffset.x - vx) / vw;
        const ny = (pos.y - canvasState.dragOffset.y - vy) / vh;
        canvasState.logoNormX = Math.max(0.0, Math.min(0.95, nx));
        canvasState.logoNormY = Math.max(0.0, Math.min(0.95, ny));
    } else if (canvasState.activeMode === "drag_subtitle") {
        const ny = (pos.y - canvasState.dragOffset.y - vy) / vh;
        canvasState.subNormY = Math.max(0.0, Math.min(0.95, ny));
    } else if (canvasState.activeMode === "resize_blur_se") {
        const dx = (pos.x - canvasState.resizeStartPos.x) / vw;
        const dy = (pos.y - canvasState.resizeStartPos.y) / vh;
        canvasState.blurNormW = Math.max(0.02, Math.min(0.95, canvasState.initialBlurNormW + dx));
        canvasState.blurNormH = Math.max(0.02, Math.min(0.95, canvasState.initialBlurNormH + dy));
    } else if (canvasState.activeMode === "resize_title") {
        const diff = (pos.x - canvasState.resizeStartPos.x) + (pos.y - canvasState.resizeStartPos.y);
        canvasState.titleFontSize = Math.max(12, Math.min(80, Math.floor(canvasState.initialFontSize + diff * 0.15)));
        document.getElementById("input-title-size").value = canvasState.titleFontSize;
    } else if (canvasState.activeMode === "resize_logo") {
        const dx = (pos.x - canvasState.resizeStartPos.x) / vw;
        canvasState.logoNormW = Math.max(0.04, Math.min(0.60, canvasState.initialLogoNormW + dx));
    } else if (canvasState.activeMode === "resize_subtitle") {
        const diff = (pos.x - canvasState.resizeStartPos.x) + (pos.y - canvasState.resizeStartPos.y);
        canvasState.subFontSize = Math.max(10, Math.min(60, Math.floor(canvasState.initialSubFontSize + diff * 0.15)));
        document.getElementById("input-sub-size").value = canvasState.subFontSize;
    }
});

window.addEventListener("mouseup", () => {
    canvasState.activeMode = null;
});

// ================= TOUCH GESTURES (IPHONE / IPAD / MOBILE) =================
function getTouchPos(touch) {
    const r = canvas.getBoundingClientRect();
    return {
        x: (touch.clientX - r.left) * (canvas.width / r.width),
        y: (touch.clientY - r.top) * (canvas.height / r.height)
    };
}

canvas.addEventListener("touchstart", (e) => {
    if (e.touches.length === 1) {
        const pos = getTouchPos(e.touches[0]);
        if (canvasState.enableBlur && isInside(pos, canvasState.blurHandleSE)) {
            canvasState.activeMode = "resize_blur_se";
            canvasState.resizeStartPos = pos;
            canvasState.initialBlurNormW = canvasState.blurNormW;
            canvasState.initialBlurNormH = canvasState.blurNormH;
            e.preventDefault();
            return;
        }
        if (isInside(pos, canvasState.titleHandleRect)) {
            canvasState.activeMode = "resize_title";
            canvasState.resizeStartPos = pos;
            canvasState.initialFontSize = canvasState.titleFontSize;
            e.preventDefault();
            return;
        }

        if (isInside(pos, canvasState.logoHandleRect)) {
            canvasState.activeMode = "resize_logo";
            canvasState.resizeStartPos = pos;
            canvasState.initialLogoNormW = canvasState.logoNormW;
            e.preventDefault();
            return;
        }
        if (isInside(pos, canvasState.subHandleRect)) {
            canvasState.activeMode = "resize_subtitle";
            canvasState.resizeStartPos = pos;
            canvasState.initialSubFontSize = canvasState.subFontSize;
            e.preventDefault();
            return;
        }

        if (canvasState.enableBlur && isInside(pos, canvasState.blurRect)) {
            canvasState.activeMode = "drag_blur";
            canvasState.dragOffset = { x: pos.x - canvasState.blurRect.x, y: pos.y - canvasState.blurRect.y };
            e.preventDefault();
        } else if (isInside(pos, canvasState.titleRect)) {
            canvasState.activeMode = "drag_title";
            canvasState.dragOffset = { x: pos.x - canvasState.titleRect.x, y: pos.y - canvasState.titleRect.y };
            e.preventDefault();
        } else if (isInside(pos, canvasState.logoRect)) {
            canvasState.activeMode = "drag_logo";
            canvasState.dragOffset = { x: pos.x - canvasState.logoRect.x, y: pos.y - canvasState.logoRect.y };
            e.preventDefault();
        } else if (isInside(pos, canvasState.subRect)) {
            canvasState.activeMode = "drag_subtitle";
            canvasState.dragOffset = { x: pos.x - canvasState.subRect.x, y: pos.y - canvasState.subRect.y };
            e.preventDefault();
        }
    }
}, { passive: false });

canvas.addEventListener("touchmove", (e) => {
    if (e.touches.length === 1 && canvasState.activeMode) {
        e.preventDefault();
        const pos = getTouchPos(e.touches[0]);
        const { vx, vy, vw, vh } = getVideoRect();

        if (canvasState.activeMode === "drag_blur") {
            const nx = (pos.x - canvasState.dragOffset.x - vx) / vw;
            const ny = (pos.y - canvasState.dragOffset.y - vy) / vh;
            canvasState.blurNormX = Math.max(0.0, Math.min(0.95, nx));
            canvasState.blurNormY = Math.max(0.0, Math.min(0.95, ny));
        } else if (canvasState.activeMode === "drag_title") {
            const nx = (pos.x - canvasState.dragOffset.x - vx) / vw;
            const ny = (pos.y - canvasState.dragOffset.y - vy) / vh;
            canvasState.titleNormX = Math.max(0.0, Math.min(0.95, nx));
            canvasState.titleNormY = Math.max(0.0, Math.min(0.95, ny));
        } else if (canvasState.activeMode === "drag_logo") {
            const nx = (pos.x - canvasState.dragOffset.x - vx) / vw;
            const ny = (pos.y - canvasState.dragOffset.y - vy) / vh;
            canvasState.logoNormX = Math.max(0.0, Math.min(0.95, nx));
            canvasState.logoNormY = Math.max(0.0, Math.min(0.95, ny));
        } else if (canvasState.activeMode === "drag_subtitle") {
            const ny = (pos.y - canvasState.dragOffset.y - vy) / vh;
            canvasState.subNormY = Math.max(0.0, Math.min(0.95, ny));
        } else if (canvasState.activeMode === "resize_blur_se") {
            const dx = (pos.x - canvasState.resizeStartPos.x) / vw;
            const dy = (pos.y - canvasState.resizeStartPos.y) / vh;
            canvasState.blurNormW = Math.max(0.02, Math.min(0.95, canvasState.initialBlurNormW + dx));
            canvasState.blurNormH = Math.max(0.02, Math.min(0.95, canvasState.initialBlurNormH + dy));
        } else if (canvasState.activeMode === "resize_title") {
            const diff = (pos.x - canvasState.resizeStartPos.x) + (pos.y - canvasState.resizeStartPos.y);
            canvasState.titleFontSize = Math.max(12, Math.min(80, Math.floor(canvasState.initialFontSize + diff * 0.15)));
            document.getElementById("input-title-size").value = canvasState.titleFontSize;
        } else if (canvasState.activeMode === "resize_logo") {
            const dx = (pos.x - canvasState.resizeStartPos.x) / vw;
            canvasState.logoNormW = Math.max(0.04, Math.min(0.60, canvasState.initialLogoNormW + dx));
        } else if (canvasState.activeMode === "resize_subtitle") {
            const diff = (pos.x - canvasState.resizeStartPos.x) + (pos.y - canvasState.resizeStartPos.y);
            canvasState.subFontSize = Math.max(10, Math.min(60, Math.floor(canvasState.initialSubFontSize + diff * 0.15)));
            document.getElementById("input-sub-size").value = canvasState.subFontSize;
        }
    }
}, { passive: false });

canvas.addEventListener("touchend", () => {
    canvasState.activeMode = null;
});


// ================= SYNC INPUTS TO CANVAS STATE =================
document.getElementById("input-title-text").addEventListener("input", (e) => canvasState.titleText = e.target.value);
document.getElementById("select-title-font").addEventListener("change", (e) => canvasState.titleFontFamily = e.target.value);
document.getElementById("input-title-size").addEventListener("input", (e) => canvasState.titleFontSize = parseInt(e.target.value) || 26);
document.getElementById("input-title-color").addEventListener("input", (e) => canvasState.titleColor = e.target.value);

document.getElementById("chk-show-subtitles").addEventListener("change", (e) => {
    canvasState.showSubtitles = e.target.checked;
});
document.getElementById("select-sub-font").addEventListener("change", (e) => canvasState.subFontFamily = e.target.value);
document.getElementById("input-sub-size").addEventListener("input", (e) => canvasState.subFontSize = parseInt(e.target.value) || 18);
document.getElementById("input-sub-color").addEventListener("input", (e) => canvasState.subColor = e.target.value);

document.getElementById("chk-blur").addEventListener("change", (e) => canvasState.enableBlur = e.target.checked);
document.getElementById("slider-blur-strength").addEventListener("input", (e) => {
    canvasState.blurStrength = parseInt(e.target.value);
    document.getElementById("label-blur-strength-val").innerText = `${canvasState.blurStrength}px`;
});
document.getElementById("input-blur-tint").addEventListener("input", (e) => canvasState.blurTint = e.target.value);
document.getElementById("slider-blur-opacity").addEventListener("input", (e) => {
    canvasState.blurTintOpacity = parseInt(e.target.value);
    document.getElementById("label-blur-opacity-val").innerText = `${canvasState.blurTintOpacity}%`;
});

document.getElementById("slider-bg-vol").addEventListener("input", (e) => {
    document.getElementById("label-bg-vol-val").innerText = `${e.target.value}%`;
});

// ================= VIDEO PLAYER CONTROLS & TIME SYNC =================
function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

btnPlayPause.addEventListener("click", () => {
    if (video.paused) {
        video.play();
        btnPlayPause.innerText = "⏸ ផ្អាក";
    } else {
        video.pause();
        ttsAudioPlayer.pause();
        btnPlayPause.innerText = "▶ លេង";
    }
});

btnStop.addEventListener("click", () => {
    video.pause();
    video.currentTime = 0;
    ttsAudioPlayer.pause();
    ttsAudioPlayer.currentTime = 0;
    currentSubtitleRow = -1;
    btnPlayPause.innerText = "▶ លេង";
});

btnMuteOrig.addEventListener("click", () => {
    video.muted = !video.muted;
    btnMuteOrig.innerText = video.muted ? "🔇 សំឡេងដើម" : "🔊 សំឡេងដើម";
});

btnMuteTts.addEventListener("click", () => {
    ttsAudioPlayer.muted = !ttsAudioPlayer.muted;
    btnMuteTts.innerText = ttsAudioPlayer.muted ? "🔇 សំឡេង AI" : "🎙️ សំឡេង AI";
});

videoSeekSlider.addEventListener("input", (e) => {
    if (video.duration) {
        video.currentTime = (parseFloat(e.target.value) / 100.0) * video.duration;
    }
});

video.addEventListener("timeupdate", () => {
    if (!video.duration) return;
    videoSeekSlider.value = (video.currentTime / video.duration) * 100.0;
    timeDisplay.innerText = `${formatTime(video.currentTime)} / ${formatTime(video.duration)}`;

    // Match Active Subtitle
    const curSec = video.currentTime;
    let activeSub = null;
    let activeIdx = -1;

    for (let i = 0; i < subtitles.length; i++) {
        const s = subtitles[i];
        if (curSec >= s.start_sec && curSec <= s.end_sec) {
            activeSub = s;
            activeIdx = i;
            break;
        }
    }

    if (activeSub) {
        canvasState.subText = activeSub.text;
        highlightTableRow(activeIdx);

        if (activeIdx !== currentSubtitleRow) {
            currentSubtitleRow = activeIdx;
            // Play corresponding AI TTS audio if available
            if (activeSub.audio_url) {
                ttsAudioPlayer.src = activeSub.audio_url;
                ttsAudioPlayer.play().catch(() => {});
            }
        }
    } else {
        canvasState.subText = "";
        highlightTableRow(-1);
        if (currentSubtitleRow !== -1) {
            ttsAudioPlayer.pause();
            currentSubtitleRow = -1;
        }
    }
});

function highlightTableRow(idx) {
    const rows = document.querySelectorAll("#subtitles-tbody tr");
    rows.forEach((r, i) => {
        if (i === idx) r.classList.add("active-row");
        else r.classList.remove("active-row");
    });
}

// ================= FILE UPLOADS & DRAG/DROP =================
function handleVideoFile(file) {
    if (!file) return;

    // Instant local preview
    const blobUrl = URL.createObjectURL(file);
    video.src = blobUrl;
    video.load();
    currentVideoUrl = blobUrl;

    // Add to Episode Select immediately
    selectEpisode.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.innerText = `ភាគ 01: ${file.name}`;
    opt.dataset.url = blobUrl;
    selectEpisode.appendChild(opt);

    taskStatusLabel.innerText = "កំពុង Upload វីដេអូទៅកាន់ Server...";
    progressBarFill.style.width = "0%";
    taskProgressPercent.innerText = "0%";
    startTimer();

    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload-video", true);

    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            progressBarFill.style.width = `${percent}%`;
            taskProgressPercent.innerText = `${percent}%`;
            taskStatusLabel.innerText = `កំពុង Upload វីដេអូ (${percent}%)...`;
        }
    };

    xhr.onload = () => {
        stopTimer();
        if (xhr.status === 200) {
            const data = JSON.parse(xhr.responseText);
            if (data.success) {
                currentVideoPath = data.file_path;
                currentVideoUrl = data.file_url;
                opt.value = data.file_path;
                opt.dataset.url = data.file_url;
                taskStatusLabel.innerText = "✅ Upload វីដេអូជោគជ័យ!";
                progressBarFill.style.width = "100%";
                taskProgressPercent.innerText = "100%";
            }
        } else {
            alert("កំហុស Upload វីដេអូ: " + xhr.statusText);
        }
    };

    xhr.onerror = () => {
        stopTimer();
        alert("មិនអាចតភ្ជាប់ទៅកាន់ Server ដើម្បី Upload វីដេអូបានទេ!");
    };

    xhr.send(formData);
}

function handleSrtFile(file) {
    if (!file) return;
    taskStatusLabel.innerText = "កំពុងអាន Subtitle SRT...";

    const reader = new FileReader();
    reader.onload = async (e) => {
        const text = e.target.result;
        parseSrtTextClient(text);

        try {
            const formData = new FormData();
            formData.append("raw_text", text);
            const res = await fetch("/api/parse-srt", { method: "POST", body: formData });
            const data = await res.json();
            if (data.success && data.subtitles && data.subtitles.length > 0) {
                subtitles = data.subtitles;
                renderSubtitlesTable();
                taskStatusLabel.innerText = `✅ ទទួលបាន ${subtitles.length} Subtitles រួចរាល់!`;
            }
        } catch (err) {
            console.log("Server parse fallback:", err);
        }
    };
    reader.readAsText(file, "UTF-8");
}

function parseSrtTextClient(content) {
    if (!content) return;
    const cleanContent = content.replace(/\ufeff/g, '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
    const blocks = cleanContent.split(/\n\s*\n/);
    const parsed = [];

    blocks.forEach((block) => {
        const lines = block.trim().split('\n').map(l => l.trim()).filter(l => l);
        if (lines.length >= 1) {
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].includes('-->')) {
                    const times = lines[i].split('-->');
                    const start = times[0].trim().replace('.', ',');
                    const end = times[1].trim().replace('.', ',');
                    const text = lines.slice(i + 1).join(' ').trim();
                    if (text) {
                        const isFemale = /\[(សំឡេង)?ស្រី\]|\(ស្រី\)|ចា៎|ចាស|អូន|អ្នកនាង|កញ្ញា|លោកស្រី|ម៉ាក់|នាង/i.test(text);
                        const isThought = /\[(សំឡេង)?គិត.*?\]|\[គិត\]|\(គិតក្នុងចិត្ត\)/i.test(text);
                        parsed.push({
                            index: parsed.length,
                            start: start,
                            end: end,
                            start_sec: parseTimeToSec(start),
                            end_sec: parseTimeToSec(end),
                            text: text,
                            gender: isFemale ? (isThought ? "female_thought" : "female_normal") : (isThought ? "male_thought" : "male_normal"),
                            voice: isFemale ? "km-KH-SreymomNeural" : "km-KH-PisethNeural",
                            is_thought: isThought,
                            audio_url: null
                        });
                    }
                    break;
                }
            }
        }
    });

    if (parsed.length > 0) {
        subtitles = parsed;
        renderSubtitlesTable();
    }
}

function parseTimeToSec(str) {
    try {
        const parts = str.replace(',', '.').split(':');
        if (parts.length === 3) {
            return parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2]);
        }
    } catch (e) {
        return 0.0;
    }
    return 0.0;
}

// Drag and Drop
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        const fname = file.name.toLowerCase();
        if (fname.endsWith(".mp4") || fname.endsWith(".mkv") || fname.endsWith(".avi") || fname.endsWith(".mov") || fname.endsWith(".webm")) {
            handleVideoFile(file);
        } else if (fname.endsWith(".srt") || fname.endsWith(".txt")) {
            handleSrtFile(file);
        } else if (fname.endsWith(".png") || fname.endsWith(".jpg") || fname.endsWith(".jpeg") || fname.endsWith(".webp")) {
            handleLogoFile(file);
        }
    }
});

function handleLogoFile(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    fetch("/api/upload-logo", { method: "POST", body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                selectedLogoPath = data.file_path;
                logoImage = new Image();
                logoImage.crossOrigin = "anonymous";
                logoImage.onload = () => {
                    document.getElementById("label-logo-name").innerText = data.filename;
                    document.getElementById("label-logo-name").style.color = "#00FF99";
                };
                logoImage.src = data.file_url;
            }
        })
        .catch(err => alert("កំហុស Upload Logo: " + err));
}

document.getElementById("btn-browse-video").addEventListener("click", () => {
    const input = document.getElementById("video-file-input");
    input.value = "";
    input.click();
});
document.getElementById("video-file-input").addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) handleVideoFile(e.target.files[0]);
});

document.getElementById("btn-browse-logo").addEventListener("click", () => {
    const input = document.getElementById("logo-file-input");
    input.value = "";
    input.click();
});
document.getElementById("logo-file-input").addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) handleLogoFile(e.target.files[0]);
});

document.getElementById("btn-browse-srt").addEventListener("click", () => {
    const input = document.getElementById("srt-file-input");
    input.value = "";
    input.click();
});
document.getElementById("srt-file-input").addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) handleSrtFile(e.target.files[0]);
});

function renderSubtitlesTable() {
    const tbody = document.getElementById("subtitles-tbody");
    tbody.innerHTML = "";

    if (!subtitles || subtitles.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #64748b; padding: 20px;">ពុំទាន់មានទិន្នន័យ Subtitle ឡើយ។</td></tr>`;
        return;
    }

    subtitles.forEach((sub, idx) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${String(idx + 1).padStart(2, '0')}</td>
            <td>${sub.start}</td>
            <td>${sub.end}</td>
            <td contenteditable="true" class="cell-sub-text">${sub.text}</td>
            <td>
                <select class="select-voice-row" data-index="${idx}">
                    <option value="km-KH-PisethNeural" ${sub.voice === "km-KH-PisethNeural" && !sub.is_thought ? "selected" : ""}>សំឡេងប្រុស</option>
                    <option value="km-KH-SreymomNeural" ${sub.voice === "km-KH-SreymomNeural" && !sub.is_thought ? "selected" : ""}>សំឡេងស្រី</option>
                    <option value="km-KH-PisethNeural" ${sub.is_thought && sub.voice === "km-KH-PisethNeural" ? "selected" : ""}>សំឡេងគិតប្រុស</option>
                    <option value="km-KH-SreymomNeural" ${sub.is_thought && sub.voice === "km-KH-SreymomNeural" ? "selected" : ""}>សំឡេងគិតស្រី</option>
                </select>
            </td>
            <td style="text-align: center;" id="status-cell-${idx}">
                <span class="status-badge ${sub.audio_url ? 'status-ready' : 'status-pending'}">
                    ${sub.audio_url ? '✅ រួចរាល់' : '❌ មិនទាន់រួច'}
                </span>
            </td>
        `;

        tr.addEventListener("click", (e) => {
            if (e.target.tagName !== "SELECT" && e.target.tagName !== "BUTTON") {
                video.currentTime = sub.start_sec;
            }
        });

        tr.querySelector(".cell-sub-text").addEventListener("blur", (e) => {
            sub.text = e.target.innerText.trim();
        });

        tr.querySelector(".select-voice-row").addEventListener("change", (e) => {
            sub.voice = e.target.value;
            const selectedText = e.target.options[e.target.selectedIndex].text;
            sub.is_thought = selectedText.includes("គិត");
        });

        tbody.appendChild(tr);
    });
}

// ================= BATCH TTS GENERATION =================
document.getElementById("btn-batch-tts").addEventListener("click", async () => {
    if (!subtitles || subtitles.length === 0) {
        alert("សូមបញ្ចូល Subtitle ជាមុនសិន!");
        return;
    }

    taskStatusLabel.innerText = "កំពុងបង្កើតសំឡេង AI...";
    progressBarFill.style.width = "0%";
    taskProgressPercent.innerText = "0%";
    startTimer();

    const payload = {
        session_id: sessionId,
        items: subtitles
    };

    try {
        const res = await fetch("/api/generate-batch-tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            trackTaskProgress(data.task_id, (task) => {
                if (task.results) {
                    task.results.forEach((r) => {
                        subtitles[r.index].audio_url = r.audio_url;
                        const cell = document.getElementById(`status-cell-${r.index}`);
                        if (cell) {
                            if (r.success) {
                                cell.innerHTML = `<span class="status-badge status-ready">✅ រួចរាល់</span>`;
                            } else {
                                cell.innerHTML = `<button class="btn btn-stop" style="padding: 2px 6px; font-size: 10px;" onclick="retrySingleTTS(${r.index})">🔄 សាកម្ដងទៀត</button>`;
                            }
                        }
                    });
                }
            });
        }
    } catch (err) {
        stopTimer();
        alert("កំហុសក្នុងការបង្កើតសំឡេង: " + err);
    }
});

async function retrySingleTTS(index) {
    const sub = subtitles[index];
    const cell = document.getElementById(`status-cell-${index}`);
    if (cell) cell.innerHTML = `<span class="status-badge status-loading">⏳ កំពុងបង្កើត...</span>`;

    try {
        const res = await fetch("/api/generate-single-tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, item: sub })
        });
        const data = await res.json();
        if (data.success) {
            sub.audio_url = data.audio_url;
            if (cell) cell.innerHTML = `<span class="status-badge status-ready">✅ រួចរាល់</span>`;
        } else {
            if (cell) cell.innerHTML = `<button class="btn btn-stop" style="padding: 2px 6px; font-size: 10px;" onclick="retrySingleTTS(${index})">🔄 សាកម្ដងទៀត</button>`;
        }
    } catch (err) {
        alert("កំហុស Retry: " + err);
    }
}
window.retrySingleTTS = retrySingleTTS;

// ================= TASK PROGRESS LISTENER (SSE with Polling Fallback) =================
function trackTaskProgress(taskId, onUpdateCallback) {
    let completed = false;
    let pollInterval = null;

    function handleTaskUpdate(task) {
        if (!task) return;
        taskStatusLabel.innerText = task.status || "";
        const prog = task.progress !== undefined ? task.progress : 0;
        progressBarFill.style.width = `${prog}%`;
        taskProgressPercent.innerText = `${prog}%`;

        if (task.elapsed_sec !== undefined) {
            taskTimerLabel.innerText = formatElapsed(task.elapsed_sec);
        }

        if (onUpdateCallback) onUpdateCallback(task);

        if (task.completed) {
            completed = true;
            stopTimer();
            if (pollInterval) clearInterval(pollInterval);
            if (task.error) {
                alert("កើតមានកំហុស: " + task.error);
            }
        }
    }

    // Try EventSource (SSE) first
    let eventSource = null;
    try {
        eventSource = new EventSource(`/api/tasks/${taskId}/events`);
        eventSource.onmessage = (event) => {
            try {
                const task = JSON.parse(event.data);
                handleTaskUpdate(task);
                if (task.completed && eventSource) {
                    eventSource.close();
                }
            } catch (e) {}
        };
        eventSource.onerror = () => {
            if (eventSource) eventSource.close();
            startPollingFallback();
        };
    } catch (e) {
        startPollingFallback();
    }

    function startPollingFallback() {
        if (completed || pollInterval) return;
        pollInterval = setInterval(async () => {
            if (completed) {
                clearInterval(pollInterval);
                return;
            }
            try {
                const res = await fetch(`/api/tasks/${taskId}`);
                if (res.ok) {
                    const task = await res.json();
                    handleTaskUpdate(task);
                }
            } catch (err) {
                console.warn("Polling error:", err);
            }
        }, 800);
    }
}


// Export Result Modal Handler
function showExportResultModal(outputUrl, downloadUrl, title = "នាំចេញវីដេអូជោគជ័យ!") {
    const modal = document.getElementById("modal-export-result");
    const videoElem = document.getElementById("export-result-video");
    const linkDl = document.getElementById("link-direct-download");
    const btnNewTab = document.getElementById("btn-open-newtab");

    videoElem.src = outputUrl;
    videoElem.load();

    const dlHref = downloadUrl || outputUrl;
    linkDl.href = dlHref;
    linkDl.setAttribute("download", outputUrl.split("/").pop());

    btnNewTab.onclick = () => window.open(outputUrl, "_blank");

    modal.style.display = "flex";
}

document.getElementById("btn-close-modal-export").addEventListener("click", () => {
    document.getElementById("modal-export-result").style.display = "none";
    document.getElementById("export-result-video").pause();
});

// ================= VIDEO EXPORT =================
document.getElementById("btn-export-video").addEventListener("click", async () => {
    if (!currentVideoPath) {
        alert("សូមបញ្ចូលវីដេអូជាមុនសិន!");
        return;
    }

    const payload = {
        session_id: sessionId,
        video_path: currentVideoPath,
        subtitles: subtitles,
        bg_music_vol: parseInt(document.getElementById("slider-bg-vol").value),
        aspect_ratio: document.getElementById("select-aspect-ratio").value,
        resolution: document.getElementById("select-resolution").value,
        video_title: canvasState.titleText,
        title_norm_x: canvasState.titleNormX,
        title_norm_y: canvasState.titleNormY,
        title_color: canvasState.titleColor,
        title_font_family: canvasState.titleFontFamily,
        title_font_size: canvasState.titleFontSize,
        logo_path: selectedLogoPath,
        logo_norm_x: canvasState.logoNormX,
        logo_norm_y: canvasState.logoNormY,
        logo_norm_w: canvasState.logoNormW,
        sub_norm_y: canvasState.subNormY,
        sub_color: canvasState.subColor,
        sub_font_family: canvasState.subFontFamily,
        sub_font_size: canvasState.subFontSize,
        burn_subtitles: document.getElementById("chk-show-subtitles").checked,
        anti_detect: document.getElementById("chk-anti-detect").checked,
        flip_horizontal: document.getElementById("chk-flip").checked,
        crop_zoom: document.getElementById("chk-crop").checked,
        color_grade: document.getElementById("chk-color").checked,
        speed_shift: document.getElementById("chk-speed").checked,
        enable_blur: canvasState.enableBlur,
        blur_norm_x: canvasState.blurNormX,
        blur_norm_y: canvasState.blurNormY,
        blur_norm_w: canvasState.blurNormW,
        blur_norm_h: canvasState.blurNormH,
        blur_strength: canvasState.blurStrength,
        blur_tint: canvasState.blurTint,
        blur_tint_opacity: canvasState.blurTintOpacity
    };

    taskStatusLabel.innerText = "កំពុងរៀបចំ Export វីដេអូ...";
    progressBarFill.style.width = "0%";
    taskProgressPercent.innerText = "0%";
    startTimer();

    try {
        const res = await fetch("/api/export-video", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            trackTaskProgress(data.task_id, (task) => {
                if (task.completed && task.output_url) {
                    showExportResultModal(task.output_url, task.download_url, "🎉 នាំចេញវីដេអូជោគជ័យ!");
                }
            });
        }
    } catch (err) {
        stopTimer();
        alert("កំហុសក្នុងការ Export: " + err);
    }
});


// ================= MODALS & NEW FEATURES =================
// 1. Single Download Modal
const modalSingleDl = document.getElementById("modal-single-download");
document.getElementById("btn-modal-single-dl").addEventListener("click", () => modalSingleDl.style.display = "flex");
document.getElementById("btn-close-modal-single-dl").addEventListener("click", () => modalSingleDl.style.display = "none");
document.getElementById("btn-cancel-single-dl").addEventListener("click", () => modalSingleDl.style.display = "none");

document.getElementById("btn-start-single-dl").addEventListener("click", async () => {
    const url = document.getElementById("txt-single-download-url").value.trim();
    if (!url || !url.startsWith("http")) {
        alert("សូមបញ្ចូល Link ត្រឹមត្រូវ!");
        return;
    }

    modalSingleDl.style.display = "none";
    taskStatusLabel.innerText = "កំពុងទាញយកវីដេអូ...";
    startTimer();

    try {
        const res = await fetch("/api/download-single", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });
        const data = await res.json();
        if (data.success) {
            trackTaskProgress(data.task_id, (task) => {
                if (task.completed && task.video_file) {
                    currentVideoPath = task.video_file.file_path;
                    currentVideoUrl = task.video_file.file_url;
                    video.src = currentVideoUrl;
                    video.load();

                    selectEpisode.innerHTML = "";
                    const opt = document.createElement("option");
                    opt.value = task.video_file.file_path;
                    opt.innerText = `ភាគ 01: ${task.video_file.filename}`;
                    opt.dataset.url = task.video_file.file_url;
                    selectEpisode.appendChild(opt);
                }
            });
        }
    } catch (err) {
        stopTimer();
        alert("កំហុស Download: " + err);
    }
});

// 2. Video Splitter Modal
const modalSplit = document.getElementById("modal-split");
document.getElementById("btn-modal-split").addEventListener("click", () => modalSplit.style.display = "flex");
document.getElementById("btn-close-modal-split").addEventListener("click", () => modalSplit.style.display = "none");
document.getElementById("btn-cancel-split").addEventListener("click", () => modalSplit.style.display = "none");

const selectSplitPreset = document.getElementById("select-split-preset");
const txtCustomSplitSec = document.getElementById("txt-custom-split-sec");
selectSplitPreset.addEventListener("change", (e) => {
    txtCustomSplitSec.style.display = e.target.value === "custom" ? "inline-block" : "none";
});

document.getElementById("btn-start-split").addEventListener("click", async () => {
    if (!currentVideoPath) {
        alert("សូមបញ្ចូលវីដេអូជាមុនសិន!");
        return;
    }

    let chunkSec = parseInt(selectSplitPreset.value);
    if (selectSplitPreset.value === "custom") {
        chunkSec = parseInt(txtCustomSplitSec.value) || 60;
    }

    modalSplit.style.display = "none";
    taskStatusLabel.innerText = "កំពុងកាត់វីដេអូជាកង់ៗ...";
    startTimer();

    try {
        const res = await fetch("/api/split-video", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_path: currentVideoPath, chunk_duration_sec: chunkSec })
        });
        const data = await res.json();
        if (data.success) {
            trackTaskProgress(data.task_id, (task) => {
                if (task.completed && task.parts && task.parts.length > 0) {
                    alert(`🎉 កាត់វីដេអូបាន ${task.parts.length} ភាគជោគជ័យ!`);
                    downloadedSeriesList = task.parts;
                    selectEpisode.innerHTML = "";
                    task.parts.forEach((p, idx) => {
                        const opt = document.createElement("option");
                        opt.value = p.file_path;
                        opt.innerText = `ភាគ ${String(idx + 1).padStart(2, '0')}: ${p.filename}`;
                        opt.dataset.url = p.file_url;
                        selectEpisode.appendChild(opt);
                    });
                    currentVideoPath = task.parts[0].file_path;
                    currentVideoUrl = task.parts[0].file_url;
                    video.src = currentVideoUrl;
                    video.load();
                }
            });
        }
    } catch (err) {
        stopTimer();
        alert("កំហុស Split: " + err);
    }
});

// 3. AI Movie Recap & Highlight Cutter Modal
// Clipboard copy helper
async function copyToClipboardRobust(text) {
    if (navigator.clipboard && window.isSecureContext) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (e) {
            console.warn("navigator.clipboard failed:", e);
        }
    }
    try {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-999999px";
        textarea.style.top = "-999999px";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        const res = document.execCommand("copy");
        document.body.removeChild(textarea);
        return res;
    } catch (err) {
        console.error("Clipboard copy error:", err);
        return false;
    }
}

// 3. AI Movie Recap & Highlight Cutter Modal
const modalRecap = document.getElementById("modal-recap");
document.getElementById("btn-modal-recap").addEventListener("click", () => {
    const preview = document.getElementById("txt-recap-prompt-preview");
    if (preview) preview.value = RECAP_PROMPT_INSTRUCTION;
    modalRecap.style.display = "flex";
});
document.getElementById("btn-close-modal-recap").addEventListener("click", () => modalRecap.style.display = "none");

const RECAP_PROMPT_INSTRUCTION = `ចាប់ពីពេលនេះតទៅ សូមអ្នកដើរតួជា "អ្នកសម្រាយសាច់រឿងភាពយន្ត និងកាត់ត Highlight អាជីព (Expert Movie Recap & Smart Editor)"។ 
ភារកិច្ចចម្បងរបស់អ្នកគឺ៖ មិនមែនសម្រាយតាំងពីដើមដល់ចប់វីដេអូទេ គឺត្រូវ **ជ្រើសរើសកាត់យកតែឈុតឆាកសំខាន់ៗ (Key Highlight Scenes) ក្នុងវីដេអូដើម** មកសម្រាយសង្ខេបឱ្យខ្លី ខ្លឹម ជក់ចិត្ត និងទាក់ទាញបំផុត!

សូមអនុវត្តតាមច្បាប់តឹងរ៉ឹងទាំង ៥ នេះ៖
១. កាត់យកតែកន្លែងសំខាន់ (Highlight Scene Selection): 
   - ជ្រើសរើសតែប្លង់សំខាន់ៗនៃសាច់រឿង (ឧ. ចំណុចចាប់ផ្តើម, ចំណុចខ្ពស់/Climax, ឈុតប្រយុទ្ធ/រំភើប, និងការបញ្ចប់)។
   - កំណត់ Timecode (Start --> End) ឱ្យចំវិនាទីពិតប្រាកដនៃឈុតឆាកនោះ ព្រោះកម្មវិធីនឹងកាត់វីដេអូដើមយកតែតាមម៉ោងដែលអ្នកកំណត់នេះមកច្របាច់បញ្ចូលគ្នា។

២. ក្បាលរឿងទាក់ទាញ (Hooking Intro):
   - បើកឆាកភ្លាម ត្រូវប្រើពាក្យទាក់ទាញអារម្មណ៍អ្នកស្តាប់ភ្លាមៗ (ឧ. "រឿងរ៉ាវមិននឹកស្មានដល់បានកើតឡើង...", "តើអ្នកធ្លាប់គិតទេថា...", "កុំទាន់អាលស្លន់ស្លោ ព្រោះការពិតគឺ...")។

៣. ភាសានិទានរស់រវើក (Storytelling Tone):
   - ប្រើភាសានិយាយបែបសម្រាយរឿងខ្លី (Shorts/TikTok/Reels/Full Movie Recap) កំប្លុកកំប្លែង ជក់ចិត្ត ឬរន្ធត់។

៤. ស្លាកសំឡេងអ្នករៀបរាប់ (Voice Tag):
   - ដាក់ស្លាក [សំឡេងប្រុស] ឬ [សំឡេងស្រី] នៅដើមបន្ទាត់នីមួយៗ។

៥. ទម្រង់លទ្ធផល (Output Format):
   - ផ្តល់លទ្ធផលជាទម្រង់ SRT ស្តង់ដារនៅក្នុង Code Block តែមួយគត់។`;

function showFloatingToast(msg) {
    let toast = document.getElementById("app-floating-toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "app-floating-toast";
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            color: #0b0f19;
            font-weight: bold;
            padding: 12px 24px;
            border-radius: 30px;
            box-shadow: 0 8px 24px rgba(0, 242, 254, 0.4);
            z-index: 999999;
            font-size: 14px;
            transition: all 0.3s ease;
            text-align: center;
        `;
        document.body.appendChild(toast);
    }
    toast.innerText = msg;
    toast.style.display = "block";
    toast.style.opacity = "1";
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.style.display = "none", 300);
    }, 4000);
}

document.getElementById("btn-copy-recap-prompt").addEventListener("click", () => {
    const content = document.getElementById("txt-recap-input").value.trim();
    let fullPrompt = RECAP_PROMPT_INSTRUCTION;
    if (content) {
        fullPrompt += `\n\n====================\nខាងក្រោមនេះជាសាច់រឿង/ខ្លឹមសារវីដេអូដើមដែលត្រូវសម្រាយយក Highlight៖\n${content}`;
    }
    copyToClipboardRobust(fullPrompt);
    showFloatingToast("✅ បានចម្លង Prompt សម្រាយរឿង (ច្បាប់ទាំង ៥) ទៅ Clipboard រួចហើយ!");
});

document.getElementById("btn-auto-open-gemini-recap").addEventListener("click", () => {
    const content = document.getElementById("txt-recap-input").value.trim();
    let fullPrompt = RECAP_PROMPT_INSTRUCTION;
    if (content) {
        fullPrompt += `\n\n====================\nខាងក្រោមនេះជាសាច់រឿង/ខ្លឹមសារវីដេអូដើមដែលត្រូវសម្រាយយក Highlight៖\n${content}`;
    }

    copyToClipboardRobust(fullPrompt);
    showFloatingToast("✅ បានចម្លង Prompt ទៅ Clipboard & កំពុងបើក Gemini!");
});

document.getElementById("btn-load-recap-srt").addEventListener("click", async () => {
    const text = document.getElementById("txt-recap-input").value.trim();
    if (!text) {
        alert("សូមបិទភ្ជាប់ SRT ដែលទទួលបានពី Gemini ជាមុនសិន!");
        return;
    }

    const formData = new FormData();
    formData.append("raw_text", text);

    try {
        const res = await fetch("/api/parse-srt", { method: "POST", body: formData });
        const data = await res.json();
        if (data.success && data.subtitles && data.subtitles.length > 0) {
            subtitles = data.subtitles;
            renderSubtitlesTable();
            modalRecap.style.display = "none";
            taskStatusLabel.innerText = `✅ បានបញ្ចូល ${subtitles.length} ឈុត Subtitle/Highlight ពី Gemini!`;
            alert(`🎉 បានបញ្ចូល ${subtitles.length} ឈុតជោគជ័យ! អ្នកអាចចុច "🎬 កាត់ Highlight" ឬ "🎬 នាំចេញវីដេអូ" បានភ្លាមៗ!`);
        } else {
            alert("ពុំអាចរកឃើញទម្រង់ SRT ត្រឹមត្រូវឡើយ។ សូមពិនិត្យមើលអត្ថបទ SRT ម្តងទៀត!");
        }
    } catch (err) {
        alert("កំហុសក្នុងការ Parse: " + err);
    }
});


document.getElementById("btn-extract-highlights").addEventListener("click", async () => {
    if (!currentVideoPath) {
        alert("សូមបញ្ចូលវីដេអូជាមុនសិន!");
        return;
    }
    if (!subtitles || subtitles.length === 0) {
        alert("សូមឱ្យ Gemini សម្រាយរឿង និងកំណត់ Timecode Highlight ជាមុនសិន!");
        return;
    }

    modalRecap.style.display = "none";
    taskStatusLabel.innerText = "កំពុងកាត់ & ច្របាច់ឈុត Highlight...";
    startTimer();

    try {
        const res = await fetch("/api/export-highlights", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_path: currentVideoPath, highlights: subtitles, session_id: sessionId })
        });
        const data = await res.json();
        if (data.success) {
            trackTaskProgress(data.task_id, (task) => {
                if (task.completed && task.output_url) {
                    currentVideoPath = task.output_path;
                    currentVideoUrl = task.output_url;
                    video.src = currentVideoUrl;
                    video.load();
                    showExportResultModal(task.output_url, task.download_url, "🎉 កាត់ & ច្របាច់វីដេអូ Highlight ជោគជ័យ!");
                }
            });
        }
    } catch (err) {
        stopTimer();
        alert("កំហុស Export Highlight: " + err);
    }
});

// 4. Batch Download Modal
const modalDownload = document.getElementById("modal-download");
document.getElementById("btn-modal-download").addEventListener("click", () => modalDownload.style.display = "flex");
document.getElementById("btn-close-modal-download").addEventListener("click", () => modalDownload.style.display = "none");
document.getElementById("btn-cancel-download").addEventListener("click", () => modalDownload.style.display = "none");

document.getElementById("btn-start-download").addEventListener("click", async () => {
    const raw = document.getElementById("txt-download-urls").value.trim();
    if (!raw) return;

    const urls = raw.split("\n").map(l => l.trim()).filter(l => l.startsWith("http"));
    if (urls.length === 0) {
        alert("សូមបញ្ចូល Link ត្រឹមត្រូវ!");
        return;
    }

    modalDownload.style.display = "none";
    taskStatusLabel.innerText = "កំពុងទាញយកវីដេអូ...";
    startTimer();

    try {
        const res = await fetch("/api/download-batch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ urls })
        });
        const data = await res.json();
        if (data.success) {
            trackTaskProgress(data.task_id, (task) => {
                if (task.completed && task.video_files && task.video_files.length > 0) {
                    downloadedSeriesList = task.video_files;
                    selectEpisode.innerHTML = "";
                    task.video_files.forEach((v, idx) => {
                        const opt = document.createElement("option");
                        opt.value = v.file_path;
                        opt.innerText = `ភាគ ${String(idx + 1).padStart(2, '0')}: ${v.filename}`;
                        opt.dataset.url = v.file_url;
                        selectEpisode.appendChild(opt);
                    });

                    currentVideoPath = task.video_files[0].file_path;
                    currentVideoUrl = task.video_files[0].file_url;
                    video.src = currentVideoUrl;
                    video.load();
                }
            });
        }
    } catch (err) {
        stopTimer();
        alert("កំហុសក្នុងការ Download: " + err);
    }
});

// Episode Switch
selectEpisode.addEventListener("change", (e) => {
    const selectedOpt = selectEpisode.options[selectEpisode.selectedIndex];
    if (selectedOpt && selectedOpt.dataset.url) {
        currentVideoPath = selectedOpt.value;
        currentVideoUrl = selectedOpt.dataset.url;
        video.src = currentVideoUrl;
        video.load();
    }
});

// Gemini Subtitle Modal
const SUBTITLE_PROMPT_INSTRUCTION = `ចាប់ពីពេលនេះតទៅ សូមអ្នកដើរតួជា អ្នកបកប្រែខ្សែភាពយន្តនិងរឿងភាគអាជីព (Expert Subtitler & Dubbing Translator)។ ភារកិច្ចចម្បងរបស់អ្នកគឺទាញយកសំឡេងសន្ទនាពីវីដេអូដែលខ្ញុំបានភ្ជាប់ ឬបកប្រែរាល់អត្ថបទដែលខ្ញុំផ្តល់ឲ្យ មកជាភាសាខ្មែរឲ្យបានស្តង់ដារបំផុត ដោយផ្តោតសំខាន់លើ'ភាសានិយាយ' ដែលរលូន ស៊ីអារម្មណ៍ និងត្រូវសំឡេងតួអង្គ ១០០%។

សូមអនុវត្តតាមច្បាប់ទាំង ៤ នេះយ៉ាងតឹងរ៉ឹង៖
1. ភាសានិយាយធម្មជាតិ (Natural Spoken Language): ហាមដាច់ខាតការបកប្រែតាមបែបសរសេរស្ងួតៗ។ ត្រូវប្រើប្រាស់ពាក្យពេចន៍ដែលប្រជាជនខ្មែរនិយមនិយាយប្រចាំថ្ងៃ (ណា, ណ៎, ហ្មង, តើ, អញ្ចឹង, វើយ, ហាស, ចា៎)។
2. ត្រូវសំឡេងតួអង្គនិយាយ (Match the actor's voice): ប្រើសព្វនាមហៅគ្នា (បង/អូន, ឯង/អញ, ខ្ញុំ/លោក, ពួកម៉ាក, អា...) ឲ្យត្រូវនឹងអាយុនិងឋានៈតួអង្គ។
3. បញ្ចេញមនោសញ្ចេតនា (Emotional Depth): អានការបកប្រែរួច ត្រូវតែមានអារម្មណ៍ត្រូវនឹងសាច់រឿងដើម។
4. ទម្រង់លទ្ធផល (Output Format): ផ្តល់មកជាទម្រង់ SRT នៅក្នុង Code Block។
បញ្ជាក់ប្រយោគស្រីប្រុសដោយសញ្ញា [សំឡេងស្រី] ឬ [សំឡេងប្រុស] និងប្រយោគគិតក្នុងចិត្តដោយសញ្ញា [សំឡេងគិតស្រី] [សំឡេងគិតប្រុស] នៅដើមបន្ទាត់នីមួយៗ។`;

const modalGemini = document.getElementById("modal-gemini");
document.getElementById("btn-modal-gemini").addEventListener("click", () => {
    const preview = document.getElementById("txt-sub-prompt-preview");
    if (preview) preview.value = SUBTITLE_PROMPT_INSTRUCTION;
    modalGemini.style.display = "flex";
});
document.getElementById("btn-close-modal-gemini").addEventListener("click", () => modalGemini.style.display = "none");

document.getElementById("btn-copy-sub-prompt").addEventListener("click", () => {
    const content = document.getElementById("txt-gemini-input").value.trim();
    let prompt = SUBTITLE_PROMPT_INSTRUCTION;
    if (content) {
        prompt += `\n\n====================\nខាងក្រោមនេះជា Subtitle / អត្ថបទដើមដែលត្រូវបកប្រែ៖\n${content}`;
    }
    copyToClipboardRobust(prompt);
    showFloatingToast("✅ បានចម្លង Prompt បកប្រែ (ច្បាប់ទាំង ៤) ទៅ Clipboard រួចហើយ!");
});

document.getElementById("btn-parse-direct-srt").addEventListener("click", async () => {
    const text = document.getElementById("txt-gemini-input").value.trim();
    if (!text) {
        alert("សូមបិទភ្ជាប់ SRT ដែលទទួលបានពី Gemini ជាមុនសិន!");
        return;
    }

    const formData = new FormData();
    formData.append("raw_text", text);

    try {
        const res = await fetch("/api/parse-srt", { method: "POST", body: formData });
        const data = await res.json();
        if (data.success && data.subtitles && data.subtitles.length > 0) {
            subtitles = data.subtitles;
            renderSubtitlesTable();
            modalGemini.style.display = "none";
            taskStatusLabel.innerText = `✅ បានបញ្ចូល ${subtitles.length} បន្ទាត់ Subtitle ពី Gemini!`;
            showFloatingToast(`🎉 បានបញ្ចូល ${subtitles.length} បន្ទាត់ Subtitle ជោគជ័យ!`);
        } else {
            alert("ពុំអាចរកឃើញទម្រង់ SRT ត្រឹមត្រូវឡើយ។ សូមពិនិត្យមើលអត្ថបទ SRT ម្តងទៀត!");
        }
    } catch (err) {
        alert("កំហុសក្នុងការ Parse: " + err);
    }
});

// Auto open Gemini for Subtitle Translation
document.getElementById("btn-auto-open-gemini-sub").addEventListener("click", () => {
    const content = document.getElementById("txt-gemini-input").value.trim();
    let prompt = SUBTITLE_PROMPT_INSTRUCTION;
    if (content) {
        prompt += `\n\n====================\nខាងក្រោមនេះជា Subtitle / អត្ថបទដើមដែលត្រូវបកប្រែ៖\n${content}`;
    }

    copyToClipboardRobust(prompt);
    showFloatingToast("✅ បានចម្លង Prompt ទៅ Clipboard & កំពុងបើក Gemini!");
});


// Merge Videos Action
document.getElementById("btn-merge-all").addEventListener("click", async () => {
    if (downloadedSeriesList.length < 2) {
        alert("សូមទាញយក ឬបញ្ចូលយ៉ាងតិច ២ វីដេអូឡើងទៅដើម្បី Merge!");
        return;
    }

    const files = downloadedSeriesList.map(v => v.file_path);
    taskStatusLabel.innerText = "កំពុង Merge វីដេអូទាំងអស់...";
    startTimer();

    try {
        const res = await fetch("/api/merge-videos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_files: files })
        });
        const data = await res.json();
        if (data.success) {
            trackTaskProgress(data.task_id, (task) => {
                if (task.completed && task.output_url) {
                    currentVideoPath = task.output_path;
                    currentVideoUrl = task.output_url;
                    video.src = currentVideoUrl;
                    video.load();
                    showExportResultModal(task.output_url, task.download_url, "🎉 Merge វីដេអូជោគជ័យ!");
                }
            });
        }
    } catch (err) {
        stopTimer();
        alert("កំហុសក្នុងការ Merge: " + err);
    }
});

