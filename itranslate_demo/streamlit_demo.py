"""
iTranslate Demo — Streamlit UI
================================
A visual, interactive demo of AssemblyAI's Universal-3 Pro real-time
streaming transcription, built for the iTranslate hardware use-case.

Run:
    1. Add your API key to the ../.env file: ASSEMBLYAI_API_KEY=your_key
    2. python3 -m streamlit run streamlit_demo.py
"""

import os
import time
import threading
import queue
import streamlit as st
from dotenv import load_dotenv

# Load API key from ../.env (repo root)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="iTranslate Demo — AssemblyAI Universal-3 Pro",
    page_icon="🎙️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS for premium look
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .main { background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%); }

    .stApp {
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%);
    }

    .hero-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5, #00d2ff);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: gradient 3s ease infinite;
        margin-bottom: 0;
    }

    @keyframes gradient {
        0% { background-position: 0% center; }
        50% { background-position: 100% center; }
        100% { background-position: 0% center; }
    }

    .hero-subtitle {
        color: #8892b0;
        font-size: 1.1rem;
        font-weight: 300;
        margin-top: 0;
    }

    .transcript-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 24px;
        min-height: 300px;
        max-height: 450px;
        overflow-y: auto;
        font-family: 'Inter', monospace;
        font-size: 1.05rem;
        line-height: 1.8;
        color: #ccd6f6;
    }

    .transcript-line {
        padding: 6px 0;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        animation: fadeIn 0.3s ease-in;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(4px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .stat-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
    }

    .stat-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #64ffda;
    }

    .stat-label {
        color: #8892b0;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .arch-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 24px;
        color: #ccd6f6;
    }

    .badge {
        display: inline-block;
        background: rgba(100, 255, 218, 0.1);
        color: #64ffda;
        border: 1px solid rgba(100, 255, 218, 0.3);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        font-weight: 500;
        margin: 2px;
    }

    .pulse-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #64ffda;
        animation: pulse 1.5s infinite;
        margin-right: 8px;
    }

    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(100, 255, 218, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(100, 255, 218, 0); }
        100% { box-shadow: 0 0 0 0 rgba(100, 255, 218, 0); }
    }

    div[data-testid="stButton"] button {
        border-radius: 12px;
        font-weight: 600;
        padding: 12px 32px;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
if "transcripts" not in st.session_state:
    st.session_state.transcripts = []
if "is_streaming" not in st.session_state:
    st.session_state.is_streaming = False
if "session_duration" not in st.session_state:
    st.session_state.session_duration = 0.0
if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="hero-title">🎙️ iTranslate Demo</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Real-time Speech-to-Text powered by AssemblyAI Universal-3 Pro</p>', unsafe_allow_html=True)

# Model badges
st.markdown("""
<div style="margin-bottom: 24px;">
    <span class="badge">u3-rt-pro</span>
    <span class="badge">Code-Switching</span>
    <span class="badge">Sub-300ms Latency</span>
    <span class="badge">16kHz PCM</span>
    <span class="badge">6 Languages</span>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Layout: Transcript + Stats
# ---------------------------------------------------------------------------
col_main, col_side = st.columns([3, 1])

with col_main:
    # Controls
    c1, c2, c3 = st.columns([1, 1, 3])

    api_key = os.environ.get("ASSEMBLYAI_API_KEY", "")

    with c1:
        start_btn = st.button("🎤 Start Listening", type="primary", use_container_width=True, disabled=st.session_state.is_streaming)
    with c2:
        stop_btn = st.button("⏹ Stop", use_container_width=True, disabled=not st.session_state.is_streaming)

    if start_btn and api_key:
        st.session_state.is_streaming = True
        st.session_state.transcripts = []
        st.session_state.turn_count = 0
        st.rerun()

    if stop_btn:
        st.session_state.is_streaming = False
        if getattr(st.session_state, "streamer", None):
            st.session_state.streamer.stop()
            st.session_state.streamer = None
        st.rerun()

    # Status indicator
    if st.session_state.is_streaming:
        st.markdown('<div><span class="pulse-dot"></span> <span style="color: #64ffda; font-weight: 500;">Listening...</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color: #8892b0; font-size: 0.9rem;">⏸ Idle — Press Start to begin transcription</div>', unsafe_allow_html=True)

    # Transcript display
    st.markdown("#### Live Transcription")

    if st.session_state.is_streaming and api_key:
        # Real streaming with AssemblyAI
        transcript_container = st.empty()
        status_text = st.empty()

        try:
            import queue
            from assemblyai_service import AssemblyAIStreamer

            transcript_queue = queue.Queue()
            error_queue = queue.Queue()

            if getattr(st.session_state, "streamer", None):
                st.session_state.streamer.stop()

            streamer = AssemblyAIStreamer(api_key, transcript_queue, error_queue)
            st.session_state.streamer = streamer
            streamer.start_in_thread()

            start_time = time.time()
            lines = []
            
            # CSS for the pipeline states
            pipeline_states = {
                "STT": "#64ffda",
                "LLM": "#00d2ff",
                "TTS": "#b678ff"
            }

            while st.session_state.is_streaming:
                try:
                    msg = transcript_queue.get(timeout=0.5)
                    
                    if msg[0] == "turn":
                        text = msg[1]
                        is_final = msg[2]
                        
                        if is_final and text.strip():
                            lines.append((text, "STT"))
                            st.session_state.turn_count += 1
                        
                        display_lines = lines[-15:]  # Keep last 15 actions
                        html = ""
                        for line_text, state in display_lines:
                            color = pipeline_states.get(state, "#ccd6f6")
                            if state == "STT":
                                html += f'<div class="transcript-line"><span class="badge" style="color:{color}; border-color:{color};">STT</span> {line_text}</div>'
                            elif state == "LLM":
                                html += f'<div class="transcript-line" style="background: rgba(0, 210, 255, 0.05);"><span class="badge" style="color:{color}; border-color:{color};">LLM Gateway</span> {line_text}</div>'
                            elif state == "TTS":
                                html += f'<div class="transcript-line" style="border-left: 2px solid {color}; padding-left: 10px;"><span class="badge" style="color:{color}; border-color:{color};">TTS Audio</span> <em>Synthesized and streamed to device</em> 🔊</div>'
                                
                        if not is_final and text.strip():
                            html += f'<div class="transcript-line" style="color: #5a6680; font-style: italic;">{text} ...</div>'
                            
                        transcript_container.markdown(f'<div class="transcript-box">{html}</div>', unsafe_allow_html=True)

                    elif msg[0] == "translating":
                        # Add a loading state for translation
                        html = ""
                        for line_text, state in lines[-15:]:
                            color = pipeline_states.get(state, "#ccd6f6")
                            if state == "STT":
                                html += f'<div class="transcript-line"><span class="badge" style="color:{color}; border-color:{color};">STT</span> {line_text}</div>'
                            else:
                                html += f'<div class="transcript-line"><span class="badge" style="color:{color}; border-color:{color};">{state}</span> {line_text}</div>'
                        html += f'<div class="transcript-line" style="color: #00d2ff; font-style: italic;"><span class="pulse-dot" style="background:#00d2ff;"></span> Translating via LLM Gateway...</div>'
                        transcript_container.markdown(f'<div class="transcript-box">{html}</div>', unsafe_allow_html=True)

                    elif msg[0] == "translated":
                        lines.append((msg[1], "LLM"))
                        
                    elif msg[0] == "tts":
                        lines.append((msg[1], "TTS"))

                    elif msg[0] == "status":
                        status_text.markdown(f"*{msg[1]}*")

                    elif msg[0] == "terminated":
                        status_text.markdown(f"*Session ended: {msg[1]}*")
                        st.session_state.is_streaming = False

                except queue.Empty:
                    pass

                if not error_queue.empty():
                    err = error_queue.get()
                    st.error(f"Stream error: {err}")
                    st.session_state.is_streaming = False
                    break

                st.session_state.session_duration = time.time() - start_time

            st.session_state.transcripts = lines

        except ImportError as e:
            st.error(f"Missing dependency: {e}. Run: `pip install assemblyai pyaudio`")
            st.session_state.is_streaming = False

    else:
        # Show previous transcripts or placeholder
        if st.session_state.transcripts:
            pipeline_states = {
                "STT": "#64ffda",
                "LLM": "#00d2ff",
                "TTS": "#b678ff"
            }
            html = ""
            for line_text, state in st.session_state.transcripts:
                color = pipeline_states.get(state, "#ccd6f6")
                if state == "STT":
                    html += f'<div class="transcript-line"><span class="badge" style="color:{color}; border-color:{color};">STT</span> {line_text}</div>'
                elif state == "LLM":
                    html += f'<div class="transcript-line" style="background: rgba(0, 210, 255, 0.05);"><span class="badge" style="color:{color}; border-color:{color};">LLM Gateway</span> {line_text}</div>'
                elif state == "TTS":
                    html += f'<div class="transcript-line" style="border-left: 2px solid {color}; padding-left: 10px;"><span class="badge" style="color:{color}; border-color:{color};">TTS Audio</span> <em>Synthesized and streamed to device</em> 🔊</div>'
                else:
                    html += f'<div class="transcript-line">{line_text}</div>'
            st.markdown(f'<div class="transcript-box">{html}</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="transcript-box" style="display: flex; align-items: center; justify-content: center; color: #5a6680;">
                <div style="text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 12px;">🎤</div>
                    <div>Set your <code>ASSEMBLYAI_API_KEY</code> environment variable and click Start</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    if not api_key:
        st.warning("⚠️ Set `ASSEMBLYAI_API_KEY` env variable to enable live streaming.")

with col_side:
    # Stats panel
    st.markdown("#### Session Stats")

    st.markdown(f"""
    <div class="stat-card" style="margin-bottom: 12px;">
        <div class="stat-value">{st.session_state.session_duration:.1f}s</div>
        <div class="stat-label">Duration</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-card" style="margin-bottom: 12px;">
        <div class="stat-value">{st.session_state.turn_count}</div>
        <div class="stat-label">Turns</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-card" style="margin-bottom: 12px;">
        <div class="stat-value">{len(st.session_state.transcripts)}</div>
        <div class="stat-label">Transcripts</div>
    </div>
    """, unsafe_allow_html=True)

    # Model info
    st.markdown("#### Model Config")
    st.markdown("""
    <div class="arch-box">
        <div style="margin-bottom: 8px;"><strong style="color: #64ffda;">Model:</strong> <code>u3-rt-pro</code></div>
        <div style="margin-bottom: 8px;"><strong style="color: #64ffda;">Sample Rate:</strong> 16kHz</div>
        <div style="margin-bottom: 8px;"><strong style="color: #64ffda;">Encoding:</strong> pcm_s16le</div>
        <div style="margin-bottom: 8px;"><strong style="color: #64ffda;">Latency:</strong> ~300ms</div>
        <div><strong style="color: #64ffda;">Languages:</strong> EN, ES, FR, DE, IT, PT</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Architecture Section
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🏗️ Proposed Architecture for iTranslate Device")

arch_col1, arch_col2 = st.columns(2)

with arch_col1:
    st.markdown("""
    <div class="arch-box">
        <h4 style="color: #64ffda; margin-top: 0;">End-to-End Pipeline</h4>
        <div style="font-family: monospace; font-size: 0.9rem; line-height: 2;">
            <div>📱 <strong>Device Microphone</strong></div>
            <div style="color: #5a6680;">  │ raw PCM audio (16kHz, 16-bit, mono)</div>
            <div style="color: #5a6680;">  ▼</div>
            <div>📡 <strong>WiFi/Cellular → WebSocket</strong></div>
            <div style="color: #5a6680;">  │ streaming.assemblyai.com:443</div>
            <div style="color: #5a6680;">  ▼</div>
            <div>🧠 <strong>AssemblyAI Universal-3 Pro</strong></div>
            <div style="color: #5a6680;">  │ real-time STT with code-switching</div>
            <div style="color: #5a6680;">  ▼</div>
            <div>🌐 <strong>Translation API</strong> (DeepL / Google)</div>
            <div style="color: #5a6680;">  │ source lang → target lang</div>
            <div style="color: #5a6680;">  ▼</div>
            <div>🔊 <strong>TTS Engine → Device Speaker</strong></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with arch_col2:
    st.markdown("""
    <div class="arch-box">
        <h4 style="color: #64ffda; margin-top: 0;">Why Universal-3 Pro?</h4>
        <div style="line-height: 1.8;">
            <div>✅ <strong>Code-switching</strong> — handles bilingual conversations natively</div>
            <div>✅ <strong>Sub-300ms latency</strong> — critical for real-time translation UX</div>
            <div>✅ <strong>94% word accuracy</strong> — best-in-class for production STT</div>
            <div>✅ <strong>Cloud-based</strong> — no GPU needed on device</div>
            <div>✅ <strong>Promptable</strong> — can tune for domain-specific vocabulary</div>
            <div>✅ <strong>Turn detection</strong> — knows when speaker finishes (triggers translation)</div>
        </div>
        <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.08);">
            <strong style="color: #64ffda;">Bandwidth:</strong> ~32 KB/s (16kHz × 16-bit mono)<br>
            <strong style="color: #64ffda;">Protocol:</strong> WebSocket (persistent connection)<br>
            <strong style="color: #64ffda;">Auth:</strong> Temporary tokens (backend-generated)
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# AE Pitch Deck / Takeaways Section
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 📋 AE Pitch Deck: Key Takeaways")

with st.expander("View Presenter Talking Points", expanded=True):
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("""
        * **1. Zero Device Compute:** Cloud architecture means no hardware limitations. Massive cost savings on device BOM (Bill of Materials) and easy scaling.
        * **2. Native Code-Switching:** Universal-3 Pro natively handles English/Spanish mixing within single utterances. No manual toggling required.
        * **3. Improved Accuracy:** Best-in-class real-time transcription directly dictates the quality of the downstream LLM translation.
        """)
        
    with col_t2:
        st.markdown("""
        * **4. Low Latency Design:** Raw `pcm_s16le` + U3-Pro ensures the pipeline hits the '300ms rule' required for voice-agent UX over 4G LTE.
        * **5. Easy Integration:** Official Python/TypeScript SDKs eliminate WebSocket complexity—focus on translation logic, not audio streaming infrastructure.
        * **6. Enterprise Security:** SOC 2 Type 2 certified, with zero audio retention in the streaming API.
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #5a6680; font-size: 0.8rem;">
    Built for AssemblyAI Applied AI Engineering Take-Home •
    <a href="https://www.assemblyai.com/docs/streaming/universal-3-pro" style="color: #64ffda;">U3 Pro Docs</a> •
    <a href="https://www.assemblyai.com/docs/getting-started/transcribe-streaming-audio-from-a-microphone/python" style="color: #64ffda;">Streaming Tutorial</a>
</div>
""", unsafe_allow_html=True)
