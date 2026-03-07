# iTranslate Use Case — Approach Document

## Executive Summary

iTranslate's translation hardware device needs improved STT accuracy for real-time bilingual conversations. This document outlines how AssemblyAI's **Universal-3 Pro** streaming model fits their architecture, why it's the right choice, and how to integrate it.

---

## 1. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  iTranslate Hardware Device                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Mic      │───▶│ PCM      │───▶│ WiFi/    │───▶│ Speaker  │  │
│  │ (16kHz)  │    │ Encoder  │    │ Cellular │    │ (TTS out)│  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
└──────────────────────┬───────────────────▲──────────────────────┘
                       │                   │
              Raw PCM  │  WebSocket        │  Translated text
              audio    │  (wss://)         │  + TTS audio
                       ▼                   │
┌──────────────────────────────────────────┴──────────────────────┐
│  Cloud Backend Orchestration Engine                             │
│                                                                 │
│  ┌─────────────────┐   ┌─────────────────┐   ┌──────────────┐  │
│  │ AssemblyAI      │──▶│ LLM Gateway     │──▶│ TTS Engine   │  │
│  │ Universal-3 Pro │   │ (Cohere Command)│   │ (Cloud TTS)  │  │
│  │ Streaming STT   │   │                 │   │              │  │
│  └─────────────────┘   └─────────────────┘   └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow
1. **Device microphone** captures audio at 16kHz, 16-bit, mono (PCM)
2. Audio streams via **WebSocket** to AssemblyAI's cloud (`streaming.assemblyai.com`)
3. **Universal-3 Pro** transcribes in real-time with ~300ms latency, natively detecting the language (e.g., Code-Switching between English and Spanish).
4. Transcribed text and language metadata are piped directly into an **LLM Gateway (Cohere `command-a-03-2025`)** for zero-shot contextual translation.
5. Translated text is sent to a **TTS engine** (e.g., Google Cloud TTS or ElevenLabs)
6. Synthesized audio streams back to the **device speaker**

### Why Cloud-Based?
The iTranslate device has no GPU and insufficient compute for on-device inference (per the requirements). Cloud-based STT via WebSocket is the only viable path. The device only needs to:
- Capture raw PCM audio from the microphone
- Maintain a WebSocket connection over WiFi/cellular
- Play back TTS audio through the speaker

**Bandwidth requirement:** ~32 KB/s (16,000 samples/sec × 2 bytes/sample = 32,000 bytes/sec). This is well within mobile data capabilities.

---

## 2. Why Universal-3 Pro (`u3-rt-pro`)

| Capability | Benefit for iTranslate |
|---|---|
| **Native code-switching** | Handles bilingual conversations where speakers switch between EN/ES/FR/DE/IT/PT without any configuration. Critical for a translation device. |
| **Sub-300ms latency** | Real-time feel — users hear the translation almost immediately after speaking. |
| **94% word accuracy** | Best-in-class accuracy on real-world audio. English: 94.07%, Spanish: 93.6%. |
| **Turn detection** | Knows when a speaker finishes — this is the natural trigger point to send text to the translation API. |
| **Promptable** | Can prime the model with domain-specific vocabulary (medical terms, legal jargon) using natural language prompts. |
| **No custom training** | Works out of the box. No need for iTranslate to provide training data. |

**Source:** [Universal-3 Pro Streaming docs](https://www.assemblyai.com/docs/streaming/universal-3-pro)

---

## 3. Integration Code

The complete integration uses AssemblyAI's Python SDK (v3 streaming API) orchestrating the Cohere LLM:

```python
import cohere
from assemblyai.streaming.v3 import (
    StreamingClient, StreamingClientOptions,
    StreamingEvents, StreamingParameters, TurnEvent,
)

# Initialize Clients
client = StreamingClient(
    StreamingClientOptions(api_key=assemblyai_key, api_host="streaming.assemblyai.com")
)
co = cohere.Client(cohere_key)

def on_turn(self, event: TurnEvent):
    if event.end_of_turn:
        # 1. Speaker finished & language detected natively
        lang = getattr(event, "language_code", "en")
        
        # 2. Route immediately to LLM Gateway for Translation
        prompt = f"Translate the following phrase directly to Spanish: '{event.transcript}'"
        response = co.chat(model="command-a-03-2025", message=prompt, temperature=0.3)
        translated_text = response.text
        
        # 3. Stream to Synthesizer
        tts_audio = synthesize_speech(translated_text)
        play_on_device(tts_audio)

client.on(StreamingEvents.Turn, on_turn)
client.connect(StreamingParameters(
    speech_model="universal-streaming-multilingual", # Enables Code-Switching
    language_detection=True,
    sample_rate=16000,
))
client.stream(aai.extras.MicrophoneStream(sample_rate=16000))
```

**Key integration point:** The `on_turn` callback with `event.end_of_turn == True` is the natural place to trigger the LLM translation. Universal-3 Pro's turn detection handles the timing so you don't need silence-detection heuristics, and `language_detection=True` tells the Cohere prompt exactly which direction to translate.

**Source:** [Streaming tutorial](https://www.assemblyai.com/docs/getting-started/transcribe-streaming-audio-from-a-microphone/python)

---

## 4. Deployment Considerations

### Authentication
- Use **temporary authentication tokens** generated by a backend server, not hardcoded API keys on the device.
- Source: [Temporary auth tokens](https://www.assemblyai.com/docs/streaming#authenticate-with-a-temporary-token)

### Latency Budget
| Stage | Expected Latency |
|---|---|
| Audio capture + network | ~50ms |
| AssemblyAI STT | ~300ms |
| Translation API | ~100-200ms |
| TTS synthesis | ~200-500ms |
| **Total** | **~650-1050ms** |

For a translation device, sub-1-second end-to-end latency is acceptable and matches competitor devices like Pocketalk.

### Regional Endpoints
AssemblyAI offers EU-West streaming via `streaming.eu.assemblyai.com` for European deployments. This can reduce latency for EU-based users and help with GDPR compliance.

### Error Handling
- WebSocket disconnections: implement automatic reconnection with exponential backoff
- Network transitions (WiFi → cellular): buffer audio locally during the switch, then resume streaming
- Session timeout: AssemblyAI sessions have an expiry (`expires_at` in the Begin event) — reconnect before it expires

---

## 5. Demo

A complete, production-ready demonstration has been built simulating the physical device UX via a persistent Streamlit web dashboard.

The architecture is divided into two strict components to prove the cloud-offloading capability:
1. **`itranslate_demo/app/app.py`** — The simulated "Hardware Device". It contains no ML models—it just captures the mic and renders the UI.
2. **`itranslate_demo/app/assemblyai_service.py`** — The Cloud Orchestration Backend. It streams the mic to Universal-3 Pro, parses the language code, and fires the string to Cohere's API.

Run the Streamlit demo locally (requires microphone access):
```bash
cd itranslate_demo/app
export ASSEMBLYAI_API_KEY="your_key"
export COHERE_API_KEY="your_key"
python3 -m streamlit run app.py
```
