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
2. Opens a persistent WebSocket connection to `wss://streaming.assemblyai.com`.
3. Streams your live voice in rapid chunks, catching partial transcripts.
4. When a turn is finalized, it dynamically calculates the latency and extracts the natively detected language (`[ES]`, `[EN]`), simulating a pass-through to an LLM Gateway.

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

## 📁 Key Assets
*   `app/app.py`: The Main Streamlit UI and dashboard logic.
*   `app/assemblyai_service.py`: The multithreaded Python WebSocket controller handling the STT stream.
*   `iTranslate_Pitch_Deck.md`: The 10-slide narrative and runbook for the Account Executive pitch.
*   `approach_document.md`: The technical executive summary of the STT pipeline integration.
