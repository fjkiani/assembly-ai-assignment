# iTranslate Streaming Voice Pipeline

**👉 Live Sales Demo Dashboard:** [https://itranslate.streamlit.app](https://itranslate.streamlit.app)

*(Note: The cloud demo URL is strictly for visual dashboard inspection without a local GPU. To actually stream voice data and use the microphone, you must run the app locally so it can securely access your physical device hardware.)*

## 📖 The Business Context

**The Problem:** iTranslate produces a physical pocket translator device connected over 4G LTE. Their current on-device speech-to-text (STT) models drain the battery rapidly, struggle with users who switch languages mid-sentence (e.g., "Spanglish"), and introduce significant latency.

**The Solution:** This project demonstrates offloading the heavy STT compute entirely to the cloud using **AssemblyAI's Universal-3 Pro API**. By piping raw 16kHz PCM audio directly to the AssemblyAI WebSocket, we achieve:
1. **Zero On-Device STT Compute:** Extending device battery life.
2. **Native Code-Switching:** Transcribing multiple languages natively without explicit language hints.
3. **Sub-300ms Latency:** Critical for conversational UI and downstream LLM translation pipelines.

## 🏗️ How it Works

This repository contains a fully containerized **Streamlit interactive dashboard** that visually simulates the iTranslate device pipeline. 

When you click "Start Listening", the application:
1. Spawns a background daemon thread that securely hooks into your local microphone (using `pyaudio`).
2. Opens a persistent WebSocket connection to `wss://streaming.assemblyai.com`, optionally injecting **domain-specific keyterms** (e.g., medical jargon, brand names) via `keyterms_prompt` to boost recognition accuracy at both word-level and turn-level.
3. Streams your live voice in rapid chunks, catching partial transcripts.
4. When a turn is finalized, it dynamically calculates the latency and extracts the natively detected language (`[ES]`, `[EN]`), simulating a pass-through to an LLM Gateway.

An **"STT Tuning" toggle** in the UI lets the AE switch Keyterms Prompting on/off to demonstrate the impact of domain-specific vocabulary boosting.

## 🔌 Running Locally (Microphone Enabled)

To use your physical microphone and test the actual latency and code-switching capabilities, you must run this on your local machine:

**1. Clone and Install Dependencies:**
```bash
cd itranslate_demo/app
pip install -r requirements.txt
```

**2. Setup Authentication:**
Create a `.env` file or export your AssemblyAI API key in the terminal.
```bash
export ASSEMBLYAI_API_KEY="your_api_key_here"
```

**3. Launch the Application:**
```bash
streamlit run app.py
```

## ☁️ Cloud Deployment Notes (Streamlit Community Cloud)
The source code has been structured specifically inside the `app/` directory to allow easy dashboard deployment to services like [Streamlit Community Cloud](https://share.streamlit.io/). 

To deploy the dashboard frontend:
1. Aim the cloud main file path to: `itranslate_demo/app/app.py`
2. Add your `ASSEMBLYAI_API_KEY` into the platform's Environment/Secrets manager. 
3. *Note on `pyaudio`*: Cloud containers (like Debian instances) do not have physical hardware microphones attached. The included `packages.txt` ensures the C-level Linux audio headers (`portaudio19-dev`) compile successfully so the app boots without crashing, but the "Start Listening" button cannot capture your voice unless run locally.

## 📁 Architecture Mapping in Code

To align with the **"Device vs. Cloud"** architectural pitch, the codebase is explicitly split into two decoupled components so the Account Executive can clearly demonstrate the offloading mechanism:

### 1. The Frontend Device (`app/app.py`)
This file represents the physical iTranslate handheld unit. It is intentionally "dumb". It contains **zero** machine learning logic and zero translation logic. Its only job is to capture the user's microphone array and render the visual dashboard metadata it receives from the cloud. 

### 2. The Cloud Orchestration Engine (`app/assemblyai_service.py`)
This file represents the powerful remote cloud backend. It executes the exact three-step "LLM Gateway" pipeline proposed in the architecture document:
* **Step 1 (STT):** Maintains the WebSocket connection with AssemblyAI Universal-3 Pro, parsing the `.language_code` to detect Code-Switching natively. When Keyterms Prompting is enabled, a `keyterms_prompt` parameter injects domain-specific terms (medical vocabulary, brand names like "iTranslate") that the model boosts at word-level during inference and turn-level during post-processing.
* **Step 2 (LLM Gateway):** Catches finalized transcripts (`end_of_turn=True`) and immediately pipes the text into the **Cohere System API (`command-a-03-2025`)** for extreme low-latency translation based on the detected language.
* **Step 3 (TTS Synthesizer):** Packages the translated string into a simulated TTS audio ready payload and fires it down the queue back to the UI (`app.py`).

### Supporting Documents
*   `iTranslate_Pitch_Deck.md`: The 10-slide narrative and runbook for the Account Executive pitch.
*   `approach_document.md`: The technical executive summary of the STT pipeline integration.
