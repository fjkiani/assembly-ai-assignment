Subject: Resolution for Streaming Issue + Scaling & Privacy Guidelines

Hi Team Spanglish,

Thank you for reaching out and providing the code snippet. We have completed our investigation into the connection failures you're experiencing with our Streaming API.

### 1. Executive Summary & Root Cause

The streaming failures are reproducible as a client‑side integration issue: the audio is not being sent in the format required by AssemblyAI’s real‑time WebSocket API, and the stream lifecycle handling is incomplete.

**Bug 1 — Audio Encoding Mismatch**
The Streaming API requires raw 16‑bit signed little‑endian PCM (`pcm_s16le`) or mu‑law (`pcm_mulaw`), single‑channel, with a sample rate that exactly matches the `sample_rate` query parameter. 

In your Java code, the `AudioFormat` correctly captures raw 16-bit PCM audio. However, the WebSocket connection URL to AssemblyAI is currently configured with `"encoding": "opus"`. When our servers receive raw PCM bytes but expect compressed Opus frames (which AssemblyAI does not transcode for latency reasons), the stream immediately fails.

**Fix:** Change the encoding parameter in your WebSocket URL from `"opus"` to `"pcm_s16le"`.

**Bug 2 — Missing `Configure` Message (v3 API)**
The v3 Streaming API requires a JSON `Configure` message to be sent immediately after the WebSocket connection opens, before any audio frames. This message must include the `speech_model` parameter. Without it, the server returns error code 3006: `"speech_model is a required parameter"`.

Your Java client starts streaming audio directly in `onOpen()` without sending this configuration message.

**Fix:** Send the following JSON message on `onOpen`, before any audio frames:
```json
{"type": "Configure", "speech_model": "u3-rt-pro", "language_detection": true}
```

**Best practices for production:**
*   Send binary WebSocket frames (not base64 JSON).
*   Implement explicit session open/close and exponential backoff on rate-limit errors.
*   Log connection URLs (without tokens), frame sizes, and any error codes for debugging.

### 2. Roadmap to 2,000 Concurrent Streams

AssemblyAI’s Streaming API is highly stable in production and autoscaling can support thousands of concurrent sessions. For Universal‑Streaming, AssemblyAI does not cap total concurrent active sessions; instead, it limits the number of **new streaming sessions** that can be created per minute. 

Your new‑session rate limit grows by 10% every 60 seconds when you use 70%+ of your limit. 

To safely ramp to 2,000+ concurrent bilingual streams:
*   **Controlled Load Test:** Start with 100 concurrent bilingual sessions. Stagger starting new court sessions to ramp by 10–15% per minute. Monitor error rates and latency, and extend to 2,000+ once stability is validated.
*   **Implement a session‑creation queue** to keep new sessions per minute under the current limit, allowing AssemblyAI’s automatic scaling to increase capacity over time.
*   **Handle the Termination event** returned by the WebSocket when a session ends, and use internal metrics to recycle resources promptly for long‑running courts and overlapping cases.

*Note: With Bug 2 fixed, your client now uses **Universal-3 Pro** (`speech_model: "u3-rt-pro"`), which natively supports English/Spanish code-switching — ideal for your court interpretation use case.*

### 3. Data Privacy and "No Retention" Assurances

We understand that court interpretation operates in highly sensitive environments.

**Security Posture:** AssemblyAI maintains SOC 2 Type 2 certification. Data is encrypted in transit and at rest, with strict access controls and continuous independent auditing.

**"No Retention / No Training" Configuration:** 
For Streaming, AssemblyAI offers **zero data retention** for audio and transcripts when you have opted out of model training. Audio is processed ephemerally in memory and the transcript is returned via WebSocket — neither is persisted after the session. Certain metadata (timestamps, durations) is retained for logging and billing purposes only. This configuration should be confirmed with your account team for Spanglish Ink's production environment.

**Data Flow:**
Incoming audio → Encrypted in transit to AssemblyAI → Ephemeral processing (in-memory) → Transcript returned via WebSocket → Audio/Transcript instantly destroyed on our servers. 

Any HIPAA‑grade or court‑equivalent compliance requirements regarding long-term storage rest entirely within Spanglish Ink’s own secure systems and retention policies.

If you would like to schedule a call to walk through the Java client checklist or the load testing plan, please let us know.

Best,
Applied AI Engineering Team
