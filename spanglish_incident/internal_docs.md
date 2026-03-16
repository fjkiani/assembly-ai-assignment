# Internal Engineering Memo

## A. One‑Page Internal Summary

**Customer:** Spanglish Inc. (court interpretation software)  
**Status:** External streaming outages are localized to Spanglish Ink’s integration. AssemblyAI’s Streaming API has passed verification with official samples and with our own internal test harness using `pcm_s16le` audio at 16 kHz.

**Summary** Streaming failures for Spanglish were caused by two mismatches between their Java WebSocket client and AssemblyAI's v3 streaming contract, not by any regression in our backend or platform.

1.  **Encoding mismatch:** Their client captured audio as 16 kHz mono PCM16 (pcm_s16le) but opened the WebSocket with `encoding=opus`, an unsupported encoding for the v3 streaming API, which led the server to misinterpret the audio frames and break the stream.
2.  **Missing `Configure` message:** The v3 API requires a JSON `Configure` message (with `speech_model` and optionally `language_detection`) to be sent immediately after WebSocket open, before any audio frames. Their client started streaming raw audio in `onOpen()` without this message, causing error code 3006 (`speech_model is a required parameter`).

When we aligned the URL (`encoding=pcm_s16le&sample_rate=16000`), added the `Configure` message (`speech_model: "u3-rt-pro"`, `language_detection: true`), and fixed frame sizing per the official Universal-Streaming spec, the same traffic pattern produced stable, accurate real-time transcripts. No other customers at similar or higher concurrency levels showed comparable symptoms during this period, further confirming the issue was isolated to Spanglish's client-side integration rather than platform capacity or reliability.



### Evidence for Client‑Side Fault

When we replay their traffic pattern with valid audio encoding, the `Configure` message, and recommended frame sizes, we cannot reproduce the failures.

When we intentionally send unsupported encodings (`opus`) or omit the `Configure` message, we observe the exact same error signatures they see in production (immediate disconnect for opus; error 3006 for missing speech_model). This is consistent with AssemblyAI's documented v3 streaming requirements.

No other customers at similar or larger concurrency levels (hundreds of streams) are reporting comparable symptoms, even when exercising the autoscaling behavior.

### Conclusion

Root cause is a mismatch between Spanglish Ink’s WebSocket client behavior and AssemblyAI’s documented Streaming API requirements. This is **not a regression** in our own backend or AssemblyAI’s platform. 

---

## B. Handoff Checklist for Applied AI Engineer (Returning OOO)

When you return, please execute the following list:

### 1. Review and Confirm
- [ ] Review the latest AssemblyAI Streaming API docs (focusing on encoding, `sample_rate`, frame size, and concurrency vs. session-creation limits).
- [ ] Review our integration layer: verify URL construction, token generation, binary frame sending, and any transformations applied to the audio before it hits the WebSocket.

### 2. Artifact Intake
- [ ] **Collect from Spanglish Ink:** Example audio frame dump (first few frames of one session), connection logs (timestamps, `sample_rate`, encoding), and WebSocket error logs (codes, messages).
- [ ] **Compare** to a golden path example captured from our own verified sample integration.

### 3. Final Deliverables
- [ ] Create a minimal reproducible example (client) in their preferred stack (Java) wired against AssemblyAI's v3 streaming endpoint, **including the `Configure` message** (`speech_model: "u3-rt-pro"`, `language_detection: true`), that they can drop directly into production.
- [ ] Draft a short runbook: “How to add a new court deployment,” including the ramp‑up pattern (staggering new sessions to avoid the per-minute limit), observability hooks (URL logging, frame sizes), and an escalation path if they see anomalies.
