# AssemblyAI Applied AI Engineering Take-Home

This repository contains the deliverables for the Applied AI Engineering take-home assignment. It is divided into two primary sections based on the scenario requirements.

---

## Part 1: iTranslate Demo
*(Target: A Python/TypeScript shop building translation hardware with strict compute/bandwidth constraints).*

**Directory:** `/itranslate_demo`

### Deliverables:
1. **[streamlit_demo.py](./itranslate_demo/streamlit_demo.py)**
   A functional, interactive Streamlit UI that simulates the handheld device capturing audio from the microphone and streaming it to AssemblyAI's real-time WebSocket API.
2. **[approach_document.md](./itranslate_demo/approach_document.md)**
   A technical architecture document explaining the edge-to-cloud approach, detailing why **Universal-3 Pro** is required for this use case (handling English/Spanish code-switching effortlessly), and outlining bandwidth optimization strategies for portable hardware.

---

## Part 2: Spanglish Inc. Critical Incident
*(Target: A production customer churning due to a failing Java implementation).*

**Directory:** `/spanglish_incident`

### Deliverables:
1. **[Spanglish_Fixed.java](./spanglish_incident/Spanglish_Fixed.java)**
   The corrected Java implementation. The root cause was an audio encoding mismatch (`opus` vs `pcm_s16le`). The file includes detailed block comments explaining the fixes.
2. **[customer_email.md](./spanglish_incident/customer_email.md)**
   The client-facing communication. It diplomatically explains the fix, provides instructions on how to scale immediately to 2,000 concurrent streams without hitting auto-scaling latency, and addresses their strict data privacy/retention concerns.
3. **[internal_docs.md](./spanglish_incident/internal_docs.md)**
   Internal engineering documentation containing a Root Cause Analysis (proving it was a client-side implementation error, not an AssemblyAI bug) and a structured handoff document for the returning Account Engineer.
