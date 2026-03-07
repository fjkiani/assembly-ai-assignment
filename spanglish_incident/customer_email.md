Subject: Resolution for Streaming Issue + Scaling & Privacy Guidelines

Hi Team Spanglish,

Thank you for reaching out and providing the code snippet. We have completed our investigation into the connection failures you're experiencing with our Streaming API.

### 1. Executive Summary & Root Cause

The streaming failures are reproducible as a client‑side integration issue: the audio is not being sent in the format required by AssemblyAI’s real‑time WebSocket API, and the stream lifecycle handling is incomplete.

**Audio Encoding Mismatch**
The Streaming API requires raw 16‑bit signed little‑endian PCM (`pcm_s16le`) or mu‑law (`pcm_mulaw`), single‑channel, with a sample rate that exactly matches the `sample_rate` query parameter. 

In your Java code, the `AudioFormat` correctly captures raw 16-bit PCM audio. However, the WebSocket connection URL to AssemblyAI is currently configured with `"encoding": "opus"`. When our servers receive raw PCM bytes but expect compressed Opus frames (which AssemblyAI does not transcode for latency reasons), the stream immediately fails.

**The Fix:** 
1. **Enforce required audio format:** Update the encoding parameter in your URL from `"opus"` to `"pcm_s16le"`.
2. **Send binary frames:** Ensure your WebSocket client sends binary frames (not JSON base64 chunks). Each frame should contain a small chunk of audio (e.g., 25 ms at 400 samples per frame).
3. **Harden the WebSocket client:** Implement explicit open/close per call and deterministic teardown when a call ends to prevent timeouts under load. Add robust error handling and exponential back‑off on “too many new sessions” style responses.
4. **Add observability:** Log the connection URL (without the token), timestamps, sample_rate, frame sizes, and any error codes from AssemblyAI.

### 2. Roadmap to 2,000 Concurrent Streams

AssemblyAI’s Streaming API is highly stable in production and autoscaling can support thousands of concurrent sessions. For Universal‑Streaming, AssemblyAI does not cap total concurrent active sessions; instead, it limits the number of **new streaming sessions** that can be created per minute. 

Your new‑session rate limit grows by 10% every 60 seconds when you use 70%+ of your limit. 

To safely ramp to 2,000+ concurrent bilingual streams:
*   **Controlled Load Test:** Start with 100 concurrent bilingual sessions. Stagger starting new court sessions to ramp by 10–15% per minute. Monitor error rates and latency, and extend to 2,000+ once stability is validated.
*   **Implement a session‑creation queue** to keep new sessions per minute under the current limit, allowing AssemblyAI’s automatic scaling to increase capacity over time.
*   **Handle the Termination event** returned by the WebSocket when a session ends, and use internal metrics to recycle resources promptly for long‑running courts and overlapping cases.

*Note: We highly recommend migrating to our newest model, **Universal-3 Pro** (`speech_model: "u3-rt-pro"`), which natively supports English/Spanish code-switching.*

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
