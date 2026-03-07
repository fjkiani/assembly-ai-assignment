# Spanglish Inc. — Internal Engineering Summary & Handoff

## Internal Engineering Summary

**Customer:** Spanglish Inc. (court interpretation software)
**Severity:** P1 — production streaming connections failing
**Root Cause:** Audio encoding mismatch

### Technical Analysis

The customer's Java code uses `javax.sound.sampled.TargetDataLine` which captures raw 16-bit PCM audio at 16kHz. This is `pcm_s16le` format. However, their WebSocket configuration sends `"encoding": "opus"` to our API.

Opus is a compressed codec — sending raw PCM bytes to an endpoint expecting Opus frames causes immediate failure. This is purely a client-side configuration error.

**Fix:** `"encoding": "opus"` → `"encoding": "pcm_s16le"`

**No action required from our engineering team.** The API correctly rejected the malformed payload.

### Additional Observations

1. **Security flaw:** Customer hardcodes API key in client-side Java. Recommended migration to temporary authentication tokens ([docs](https://www.assemblyai.com/docs/streaming#authenticate-with-a-temporary-token)).
2. **Model upgrade opportunity:** Universal-3 Pro (`u3-rt-pro`) natively handles English/Spanish code-switching — a perfect fit for their court interpreter use-case. Migration is a single parameter change: `speech_model: "u3-rt-pro"` ([docs](https://www.assemblyai.com/docs/streaming/universal-3-pro)).

---

## Handoff Document

**Customer:** Spanglish Inc.
**Account Status:** Paid, scaling to 2,000 concurrent streams
**Industry:** Legal / Court Interpretation
**Privacy Requirements:** Strict — zero retention + PII redaction needed

### Recent Interaction Summary

Resolved a P1 streaming failure caused by an encoding mismatch (`opus` vs `pcm_s16le`). Customer-side config error. Sent fix + recommended Universal-3 Pro for native code-switching.

### Open Action Items

| # | Item | Status | Priority |
|---|------|--------|----------|
| 1 | Verify customer submitted opt-out email to `data-opt-out@assemblyai.com` | Pending | High |
| 2 | Monitor account metrics during scale-up to 2,000 streams | Pending | Medium |
| 3 | Contact sales re: custom concurrency limit (avoid gradual ramp) | Pending | Medium |
| 4 | Follow up on API key security (temp token migration) | Pending | High |

### Key Risk

If Spanglish Inc. attempts a "thundering herd" launch (0 → 2,000 streams instantly) without a custom concurrency limit, they will hit rate limits. Default paid starting limit is 100 streams; auto-scaling increases by 10% per minute when 70% utilized ([docs](https://www.assemblyai.com/docs/guides/real-time-streaming-transcription)).
