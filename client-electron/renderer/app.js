// ─── State ───────────────────────────────────────────────────────

const State = {
  IDLE: "idle",
  RECORDING: "recording",
  PROCESSING: "processing",
};

let currentState = State.IDLE;
let currentTone = "professionale";
let availableTones = [];
let serverUrl = "http://localhost:8899";
let pendingContext = null;

// Audio recording
let audioContext = null;
let mediaStream = null;
let sourceNode = null;
let processorNode = null;
let audioChunks = [];
let silenceCheckTimer = null;
let micWarningShown = false;

// ─── WAV Encoding ────────────────────────────────────────────────

function encodeWAV(samples, sampleRate, numChannels) {
  const bytesPerSample = 2; // 16-bit
  const blockAlign = numChannels * bytesPerSample;
  const dataSize = samples.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(view, 8, "WAVE");

  // fmt chunk
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true); // chunk size
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bytesPerSample * 8, true);

  // data chunk
  writeString(view, 36, "data");
  view.setUint32(40, dataSize, true);

  // PCM samples (float32 → int16)
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }

  return new Blob([buffer], { type: "audio/wav" });
}

function writeString(view, offset, str) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

// ─── Audio Recording ─────────────────────────────────────────────

async function initAudio() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: true,
      },
    });
  } catch (err) {
    console.error("Microphone access denied:", err);
    whisprly.notify("Whisprly", "Microphone access denied");
  }
}

function startRecording() {
  if (!mediaStream) return;

  audioChunks = [];
  micWarningShown = false;

  // Check that stream tracks are still live
  const track = mediaStream.getAudioTracks()[0];
  if (!track || track.readyState !== "live" || !track.enabled) {
    whisprly.notify("Whisprly", "Microphone not available — check system settings.");
    showError("Mic unavailable");
    return false;
  }

  // Create AudioContext at 16kHz for Whisper
  audioContext = new AudioContext({ sampleRate: 16000 });
  sourceNode = audioContext.createMediaStreamSource(mediaStream);

  // ScriptProcessorNode to capture raw PCM
  // Buffer size 4096 gives good balance of latency/performance
  processorNode = audioContext.createScriptProcessor(4096, 1, 1);
  processorNode.onaudioprocess = (e) => {
    const data = e.inputBuffer.getChannelData(0);
    audioChunks.push(new Float32Array(data));
  };

  sourceNode.connect(processorNode);
  processorNode.connect(audioContext.destination);

  // After 1.5s, check if mic is actually capturing audio
  silenceCheckTimer = setTimeout(() => {
    if (currentState !== State.RECORDING || audioChunks.length === 0) return;
    let sumSquares = 0;
    let totalSamples = 0;
    for (const chunk of audioChunks) {
      for (let i = 0; i < chunk.length; i++) {
        sumSquares += chunk[i] * chunk[i];
      }
      totalSamples += chunk.length;
    }
    const rms = Math.sqrt(sumSquares / totalSamples);
    if (rms < 0.005) {
      micWarningShown = true;
      whisprly.notify("Whisprly", "Microphone seems muted — check audio input.");
      showError("Mic muted?");
    }
  }, 1500);

  return true;
}

function stopRecording() {
  if (silenceCheckTimer) {
    clearTimeout(silenceCheckTimer);
    silenceCheckTimer = null;
  }
  if (processorNode) {
    processorNode.disconnect();
    processorNode = null;
  }
  if (sourceNode) {
    sourceNode.disconnect();
    sourceNode = null;
  }
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }

  // Concatenate all chunks into a single Float32Array
  const totalLength = audioChunks.reduce((sum, c) => sum + c.length, 0);
  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (const chunk of audioChunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }

  audioChunks = [];
  return encodeWAV(merged, 16000, 1);
}

// ─── State Machine ───────────────────────────────────────────────

function setState(newState) {
  currentState = newState;
  document.body.className = newState;
  if (pendingContext && newState === State.RECORDING) {
    document.body.classList.add("context");
  }
}

function showSuccess() {
  document.body.className = "success";
  setTimeout(() => {
    if (currentState === State.IDLE) {
      document.body.className = "idle";
    }
  }, 800);
}

function showError(message) {
  document.body.className = "error";
  if (message) {
    const overlay = document.getElementById("error-overlay");
    overlay.querySelector("span").textContent = message;
    overlay.classList.remove("hidden");
    setTimeout(() => overlay.classList.add("hidden"), 3000);
  }
  setTimeout(() => {
    if (currentState === State.IDLE) {
      document.body.className = "idle";
    }
  }, 600);
}

// ─── Recording Toggle ────────────────────────────────────────────

let lastToggleTime = 0;

async function toggleRecording() {
  const now = Date.now();
  if (now - lastToggleTime < 500) return; // debounce
  lastToggleTime = now;

  if (currentState === State.PROCESSING) return;

  if (currentState === State.IDLE) {
    // Start recording
    if (startRecording() === false) return;
    setState(State.RECORDING);
    whisprly.notify("Whisprly", "Recording started... Press again to stop.");
    console.log("Recording started");
  } else if (currentState === State.RECORDING) {
    // Stop recording and process
    const wavBlob = stopRecording();
    console.log(`Recording stopped (${(wavBlob.size / 1024).toFixed(1)} KB)`);

    if (wavBlob.size < 1000) {
      whisprly.notify("Whisprly", "Recording too short, ignored.");
      setState(State.IDLE);
      return;
    }

    setState(State.PROCESSING);
    whisprly.notify("Whisprly", "Processing...");

    try {
      const formData = new FormData();
      formData.append("audio", wavBlob, "recording.wav");
      formData.append("tone", currentTone);
      if (pendingContext) {
        formData.append("context", pendingContext);
      }

      const response = await fetch(`${serverUrl}/process`, {
        method: "POST",
        body: formData,
        signal: AbortSignal.timeout(60000),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Server error: ${response.status}`);
      }

      const result = await response.json();
      console.log("Raw:", result.raw_text);
      console.log("Clean:", result.clean_text);

      // Auto-paste the result
      await whisprly.autoPaste(result.clean_text);

      // Save to history
      whisprly.saveHistoryEntry({
        cleanText: result.clean_text,
        rawText: result.raw_text,
        tone: currentTone,
        hasContext: !!pendingContext,
      });

      const preview = result.clean_text.slice(0, 100);
      whisprly.notify("Whisprly", `Pasted!\n${preview}`);

      pendingContext = null;
      setState(State.IDLE);
      showSuccess();
    } catch (err) {
      console.error("Processing error:", err);
      pendingContext = null;
      const msg =
        err.name === "TimeoutError"
          ? "Timeout: server did not respond"
          : err.message.includes("fetch")
            ? "Server unreachable"
            : err.message;
      whisprly.notify("Whisprly", `Error: ${msg}`);
      setState(State.IDLE);
      showError(msg);
    }
  }
}

// ─── Widget Drag ────────────────────────────────────────────────

let isDragging = false;
let dragStartScreenX = 0;
let dragStartScreenY = 0;
let dragStartWinX = 0;
let dragStartWinY = 0;
const DRAG_THRESHOLD = 5;

const iconEl = document.getElementById("icon-container");

iconEl.addEventListener("mousedown", async (e) => {
  if (e.button !== 0) return;

  dragStartScreenX = e.screenX;
  dragStartScreenY = e.screenY;

  const pos = await whisprly.getWindowPosition();
  dragStartWinX = pos.x;
  dragStartWinY = pos.y;

  isDragging = false;

  document.addEventListener("mousemove", onDragMove);
  document.addEventListener("mouseup", onDragEnd);
});

function onDragMove(e) {
  const dx = e.screenX - dragStartScreenX;
  const dy = e.screenY - dragStartScreenY;

  if (!isDragging && Math.abs(dx) + Math.abs(dy) > DRAG_THRESHOLD) {
    isDragging = true;
    iconEl.style.cursor = "grabbing";
  }

  if (isDragging) {
    whisprly.moveWindow(dragStartWinX + dx, dragStartWinY + dy);
  }
}

function onDragEnd() {
  document.removeEventListener("mousemove", onDragMove);
  document.removeEventListener("mouseup", onDragEnd);

  if (isDragging) {
    iconEl.style.cursor = "";
    whisprly.saveWindowPosition();
    // Prevent the click from firing after drag
    setTimeout(() => { isDragging = false; }, 50);
  }
}

// ─── Widget Click — Open Dashboard ──────────────────────────────

iconEl.addEventListener("click", () => {
  if (isDragging) return;
  if (currentState === State.IDLE) {
    whisprly.openDashboard();
  }
});

// ─── Context Menu ────────────────────────────────────────────────

iconEl.addEventListener("contextmenu", (e) => {
  e.preventDefault();
  whisprly.showContextMenu(availableTones, currentTone);
});

// ─── Initialization ──────────────────────────────────────────────

async function init() {
  // Load server URL from config
  serverUrl = await whisprly.getServerUrl();

  // Load tones
  try {
    const tonesData = await whisprly.getTones();
    availableTones = tonesData.tones || [];
    currentTone = await whisprly.getCurrentTone();
  } catch (_) {
    availableTones = ["professionale"];
  }

  // Check server health
  const healthy = await whisprly.checkHealth();
  if (!healthy) {
    const overlay = document.getElementById("error-overlay");
    overlay.querySelector("span").textContent = "Server offline";
    overlay.classList.remove("hidden");
    setTimeout(() => overlay.classList.add("hidden"), 5000);
  }

  // Init microphone
  await initAudio();

  // Listen for hotkey toggle
  whisprly.onToggleRecording(toggleRecording);

  // Listen for context recording toggle
  whisprly.onToggleRecordingWithContext((context) => {
    pendingContext = context;
    toggleRecording();
  });

  // Listen for tone changes from context menu
  whisprly.onToneChanged((tone) => {
    currentTone = tone;
    whisprly.notify("Whisprly", `Tone changed: ${tone}`);
  });

  console.log("Whisprly renderer ready");
  console.log(`Server: ${serverUrl}`);
  console.log(`Tone: ${currentTone}`);
}

init();
