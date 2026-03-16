# iTranslate Streaming Voice Pipeline

## 📖 The Business Context

**The Problem:** iTranslate produces a physical pocket translator device connected over 4G LTE. Their current on-device speech-to-text (STT) models drain the battery rapidly, struggle with users who switch languages mid-sentence (e.g., "Spanglish"), and introduce significant latency.

**The Solution:** This project demonstrates offloading the heavy STT compute entirely to the cloud using **AssemblyAI's Universal-3 Pro API**, with **Cohere** for translation and **ElevenLabs** for high-quality TTS. By piping raw 16kHz PCM audio directly to the AssemblyAI WebSocket, we achieve:
1. **Zero On-Device STT Compute:** Extending device battery life.
2. **Native Code-Switching:** Transcribing multiple languages natively without explicit language hints.
3. **Sub-300ms Latency:** Critical for conversational UI and downstream LLM translation pipelines.
4. **Real-Time Video Dubbing:** Pause → translate → speak → resume cycle driven by natural turn detection.

## 🏗️ How it Works

The demo is a **Next.js web application** that implements a real-time video dubbing pipeline. You load a YouTube video, click **Start Dubbing**, and the system:

1. Captures video audio via the **Web Audio API** (`createMediaElementSource`), downsamples to 16kHz PCM, and buffers into 100ms chunks.
2. Streams audio over **WebSocket** to `wss://streaming.assemblyai.com/v3/ws` using a temporary auth token (API key stays server-side).
3. Universal-3 Pro transcribes in real-time with native language detection and fires **turn events** (`end_of_turn`) when the speaker finishes.
4. On each turn, the browser **pauses the video**, sends the transcript to the **Cohere Command-A** LLM for translation (via `/api/translate`).
5. Translated text is sent to **ElevenLabs TTS** (via `/api/tts`) and played through the browser speakers.
6. When TTS playback finishes, the video **resumes automatically**.

An **"STT Tuning" toggle** lets you switch Keyterms Prompting on/off to demonstrate the impact of domain-specific vocabulary boosting (medical terms, brand names).

## 🔌 Running Locally

**Prerequisites:**
- Node.js 18+
- `yt-dlp` installed (`brew install yt-dlp` on macOS)

**1. Install Dependencies:**
```bash
cd itranslate_demo/web
npm install
```

**2. Setup Authentication:**
Create a `.env.local` file with your API keys:
```bash
ASSEMBLYAI_API_KEY=your_assemblyai_key
COHERE_API_KEY=your_cohere_key
ELEVENLABS_API_KEY=your_elevenlabs_key
```

**3. Launch the Application:**
```bash
npm run dev
# Open http://localhost:3000
```

**4. Start Dubbing:**
- The demo video URL is pre-loaded. Click **Start Dubbing** to begin.
- To use a different video, paste a YouTube URL and click **Download**.

## 📁 Architecture Mapping in Code

### Cloud Orchestration (Next.js API Routes)
All API keys and external service calls stay server-side for security:

| Route | Service | Purpose |
|-------|---------|---------|
| `/api/token` | AssemblyAI | Generates temporary auth tokens for browser WebSocket |
| `/api/translate` | Cohere `command-a-03-2025` (v2/chat) | LLM Gateway — translates STT transcript based on detected language |
| `/api/tts` | ElevenLabs | Text-to-Speech synthesis, returns MP3 audio stream |
| `/api/video/download` | yt-dlp | Downloads YouTube videos to `public/videos/` |

### Browser Client (React Hooks)

| Hook | Purpose |
|------|---------|
| `useVideoDubbing.js` | Core orchestration: video → audio capture → WebSocket → pause → translate → speak → resume |
| `useElevenLabsTTS.js` | ElevenLabs TTS playback (fetches from `/api/tts`, returns Promise that resolves when audio finishes) |
| `useTranscription.js` | General-purpose mic streaming hook (reusable for live mic mode) |

### Key Technical Details

- **Audio chunking:** Browser's `ScriptProcessorNode` fires at the system audio rate (44.1/48kHz). Audio is downsampled to 16kHz and buffered into ≥100ms (3200-byte) chunks before sending to AssemblyAI (which requires 50–1000ms per frame).
- **WebSocket config:** v3 protocol uses URL query params (`sample_rate=16000&speech_model=u3-rt-pro`), not a JSON Configure message.
- **Temp tokens:** Generated server-side via `GET /v3/token?expires_in_seconds=300` and passed to the browser for WebSocket auth.
- **Turn detection:** Universal-3 Pro uses punctuation-based turn detection controlled by `min_turn_silence` / `max_turn_silence`.

### Supporting Documents
- `approach_document.md`: The technical architecture document with data flow diagrams and latency analysis.

### Legacy (Streamlit)
The original Streamlit demo is preserved in `app/` for reference:
- `app/app.py` — Streamlit UI (mic capture, dashboard)
- `app/assemblyai_service.py` — Python cloud orchestration
