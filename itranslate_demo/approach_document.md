# iTranslate Use Case — Approach Document

## Executive Summary

iTranslate's translation hardware device needs improved STT accuracy for real-time bilingual conversations. This document outlines how AssemblyAI's **Universal-3 Pro** streaming model fits their architecture, why it's the right choice, and how to integrate it.

---

## 1. Architecture: The Cloud-Centric Pipeline

The iTranslate device has no GPU and limited edge compute. Therefore, the architecture must rely on a lightweight on-device client that only handles audio capture and transport, offloading all heavy inferences (STT, Translation, TTS) to the cloud.

AssemblyAI’s **Universal-Streaming API** is designed exactly for this low‑latency, conversational use case.

```
┌──────────────────────────────────────────────────────────────────┐
│  iTranslate Hardware Device (Edge)                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │
│  │ Mic      │───▶│ Encode   │───▶│ WebSocket│                   │
│  │ (16kHz)  │    │ pcm_s16le│    │ Client   │                   │
│  └──────────┘    └──────────┘    └──────────┘                   │
│       ▲                                │                        │
│       │                                ▼                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │
│  │ Speaker  │◀───│ Decode   │◀───│ Playback │                   │
│  │ (TTS out)│    │          │    │ Stream   │                   │
│  └──────────┘    └──────────┘    └──────────┘                   │
└──────────────────────────────────────────────────────────────────┘
                                 │ ▲
                 Raw PCM (16kHz) │ │ TTS Audio Stream
                                 ▼ │
┌──────────────────────────────────────────────────────────────────┐
│  Cloud Pipeline (Python / TypeScript Backend)                   │
│                                                                 │
│  ┌─────────────────┐   ┌─────────────────┐   ┌──────────────┐  │
│  │ AssemblyAI      │──▶│ LLM Gateway     │──▶│ TTS Engine   │  │
│  │ Universal-STT   │   │ (Translation)   │   │ (Cloud TTS)  │  │
│  └─────────────────┘   └─────────────────┘   └──────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow & Lifecycle
1. **Capture & Transport:** The device captures microphone audio, encodes it as mono `pcm_s16le` at a fixed 16 kHz rate, and streams it to the backend via WebSocket using small, regular chunks.
2. **Session Management:** The system maintains a single continuous connection per "conversation session."
3. **STT:** AssemblyAI's Streaming STT transcribes the audio, returning partial and final transcripts in real-time.
4. **LLM Gateway Translation:** As soon as an utterance ends (a "final" transcript), the backend routes the text through the real-time translation cookbook pattern (Streaming STT + LLM Gateway) to translate the segment into the target language.
5. **TTS Playback:** The translated text is piped into a cloud-based TTS provider, and the resulting audio is streamed back down to the device for playback.

---

## 2. Integration: Python & TypeScript SDKs

Your backend services should not hand-roll WebSocket logic. Instead, utilize AssemblyAI's official SDKs.

### Python Backend (Orchestration)
The official Python SDK provides streaming client utilities to manage events, turns, and termination automatically.

```python
import assemblyai as aai
from assemblyai.streaming.v3 import StreamingClient, StreamingClientOptions, TurnEvent

# 1. Initialize AssemblyAI Client
client = StreamingClient(StreamingClientOptions(api_key="...", api_host="streaming.assemblyai.com"))

# 2. Orchestrate Translation & TTS on Turn Completion
def on_turn(self, event: TurnEvent):
    if event.end_of_turn:
        # Route to LLM Gateway for translation
        translated_text = llm_gateway_translate(event.transcript, target="es")
        # Route to TTS
        audio_stream = tts_synthesize(translated_text)
        # Stream down to device
        send_to_device(audio_stream)

client.on(aai.streaming.v3.StreamingEvents.Turn, on_turn)

# 3. Best-Practice Latency Settings
client.connect(aai.streaming.v3.StreamingParameters(
    speech_model="u3-rt-pro", 
    sample_rate=16000,
    disable_formatting=True # Trade formatting for lower latency
))
```

### TypeScript (Control Plane & Companion Apps)
The AssemblyAI TypeScript SDK can be used in a Node/Browser environment for companion apps or a web-based control plane. This layer subscribes to real-time transcript and translation updates, managing device sessions and visually displaying the conversational flow (partial captions, final text, translated output).

---

## 3. Latency vs. Accuracy Levers

For a handheld hardware translator, tuning the STT engine is critical to balancing speed and conversational accuracy.

*   **Minimizing Latency:** Configure Universal-Streaming for absolute minimum latency by using `pcm_s16le`, disabling expensive formatting options (like punctuation/casing if unnecessary for the LLM), and aggressively tuning turn-detection thresholds.
*   **Maximizing Accuracy:** Trade a small amount of latency for accuracy by using high-quality hardware audio capture and choosing **Universal-3 Pro** (`u3-rt-pro`). U3-Pro is highly optimized for short, conversational utterances and features native code-switching.
*   **Translation Quality:** By using the LLM Gateway pattern, you translate finalized segments (utterances) rather than rolling partial text. This preserves alignment and grammatical context, ensuring higher-fidelity output than real-time word-by-word literal translation.

---

## 4. Demo: The Live Bilingual Flow

Included in this repository is `streamlit_demo.py`. This UI physically demonstrates the target architectural flow for the AE/Demo narrative:

1. **Hardware Simulation:** The browser captures your microphone.
2. **STT Streaming:** Text appears instantly on screen (Partial → Final).
3. **Translation Layer:** Once a turn finalizes, the text hits a mock LLM Gateway for translation.
4. **TTS Output:** The translated text is mapped to a simulated TTS engine for playback.

Run the demo to experience the pipeline:
```bash
ASSEMBLYAI_API_KEY=<your_key> python3 -m streamlit run streamlit_demo.py
```
