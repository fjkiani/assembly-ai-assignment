# Internal Engineering Memo

## A. One‑Page Internal Summary

**Customer:** Spanglish Inc. (court interpretation software)  
**Status:** External streaming outages are localized to Spanglish Ink’s integration. AssemblyAI’s Streaming API has passed verification with official samples and with our own internal test harness using `pcm_s16le` audio at 16 kHz.

**Summary** Streaming failures for Spanglish were caused by a mismatch between their Java WebSocket client and AssemblyAI’s documented streaming contract, not by any regression in our backend or AssemblyAI’s platform. Their client captured audio as 16 kHz mono PCM16 (pcm_s16le) but opened the WebSocket with encoding=opus, an unsupported encoding for the v3 streaming API, which led the server to misinterpret the audio frames and break the stream. When we aligned the URL (encoding=pcm_s16le&sample_rate=16000) and frame sizing with the official Universal‑Streaming spec, the same traffic pattern produced stable, accurate real‑time transcripts, and we could no longer reproduce the failures. No other customers at similar or higher concurrency levels showed comparable symptoms during this period, further confirming the issue was isolated to Spanglish’s client‑side integration rather than platform capacity or reliability.



### Evidence for Client‑Side Fault

When we replay their traffic pattern with valid audio encoding and recommended frame sizes, we cannot reproduce the failures.

When we intentionally send unsupported encodings (`opus`) or wrong sample rates, we observe the exact same error signatures they see in production. This is consistent with AssemblyAI’s documented audio requirements.

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
- [ ] Create a minimal reproducible example (client) in their preferred stack (Java) wired against AssemblyAI’s streaming endpoint, that they can drop directly into production.
- [ ] Draft a short runbook: “How to add a new court deployment,” including the ramp‑up pattern (staggering new sessions to avoid the per-minute limit), observability hooks (URL logging, frame sizes), and an escalation path if they see anomalies.
