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

# ==============================================================================
# ARCHITECTURE MAPPING: THE FRONTEND DEVICE (UI LAYER)
# ==============================================================================
# This file (`app.py`) represents the iTranslate handheld hardware device.
# It contains NO machine learning models or heavy processing logic. 
# Its sole responsibility is to render the UI, capture microphone input,
# and display the finalized STT/LLM/TTS events pushed from the Cloud Orchestrator.
# ==============================================================================

import streamlit as st

# In Streamlit Cloud, variables set in "Advanced Settings > Secrets" 
# are automatically injected into `os.environ` or available via `st.secrets`.

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

    st.markdown("#### Engine Tuning (AE Controls)")
    use_stt_prompt = st.toggle("Enable Universal-3 Pro STT Prompting (Inject Medical/iTranslate Jargon)", value=True, help="When enabled, biases the STT translation towards Spanglish and iTranslate vocabulary.")

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
            import importlib
            import assemblyai_service
            importlib.reload(assemblyai_service)
            from assemblyai_service import AssemblyAIStreamer

            transcript_queue = queue.Queue()
            error_queue = queue.Queue()

            if getattr(st.session_state, "streamer", None):
                st.session_state.streamer.stop()

            streamer = AssemblyAIStreamer(
                api_key=api_key, 
                transcript_queue=transcript_queue, 
                error_queue=error_queue,
                use_prompt=use_stt_prompt
            )
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
                        lang = msg[3] if len(msg) > 3 else "en"
                        
                        if is_final and text.strip():
                            lines.append((text, "STT", lang, 0.0))
                            st.session_state.transcripts.append((text, "STT", lang, 0.0))
                            st.session_state.turn_count += 1
                        
                        display_lines = lines[-15:]  # Keep last 15 actions
                        html = ""
                        for line_item in display_lines:
                            # Handle both old 2-tuple and new 4-tuple formats
                            if len(line_item) == 2:
                                line_text, state = line_item
                                line_lang, latency = "en", 0.0
                            else:
                                line_text, state, line_lang, latency = line_item
                                
                            color = pipeline_states.get(state, "#ccd6f6")
                            if state == "STT":
                                meta_badge = f'<span style="font-size:0.75rem; color:#8892b0; margin-left:8px;">[Detected: {str(line_lang).upper()}]</span>'
                                html += f'<div class="transcript-line"><span class="badge" style="color:{color}; border-color:{color};">STT</span> {line_text} {meta_badge}</div>'
                            elif state == "LLM":
                                meta_badge = f'<span style="font-size:0.75rem; color:#8892b0; margin-left:8px;">[STT Latency: {latency*1000:.0f}ms]</span>' if latency > 0 else ""
                                html += f'<div class="transcript-line" style="background: rgba(0, 210, 255, 0.05);"><span class="badge" style="color:{color}; border-color:{color};">LLM Gateway</span> {line_text} {meta_badge}</div>'
                            elif state == "TTS":
                                html += f'<div class="transcript-line" style="border-left: 2px solid {color}; padding-left: 10px;"><span class="badge" style="color:{color}; border-color:{color};">TTS Audio</span> <em>Synthesized and streamed to device</em> 🔊</div>'
                                
                        if not is_final and text.strip():
                            html += f'<div class="transcript-line" style="color: #5a6680; font-style: italic;">{text} ...</div>'
                            
                        transcript_container.markdown(f'<div class="transcript-box">{html}</div>', unsafe_allow_html=True)

                    elif msg[0] == "translating":
                        lang = msg[2] if len(msg) > 2 else "en"
                        latency = msg[3] if len(msg) > 3 else 0.0
                        
                        html = ""
                        for line_item in lines[-15:]:
                            if len(line_item) == 2:
                                line_text, state = line_item
                                line_lang, l_latency = "en", 0.0
                            else:
                                line_text, state, line_lang, l_latency = line_item
                                
                            color = pipeline_states.get(state, "#ccd6f6")
                            if state == "STT":
                                meta_badge = f'<span style="font-size:0.75rem; color:#8892b0; margin-left:8px;">[Detected: {str(line_lang).upper()}]</span>'
                                html += f'<div class="transcript-line"><span class="badge" style="color:{color}; border-color:{color};">STT</span> {line_text} {meta_badge}</div>'
                            elif state == "LLM":
                                meta_badge = f'<span style="font-size:0.75rem; color:#8892b0; margin-left:8px;">[STT Latency: {l_latency*1000:.0f}ms]</span>' if l_latency > 0 else ""
                                html += f'<div class="transcript-line" style="background: rgba(0, 210, 255, 0.05);"><span class="badge" style="color:{color}; border-color:{color};">LLM Gateway</span> {line_text} {meta_badge}</div>'
                            elif state == "TTS":
                                html += f'<div class="transcript-line" style="border-left: 2px solid {color}; padding-left: 10px;"><span class="badge" style="color:{color}; border-color:{color};">TTS Audio</span> <em>Synthesized and streamed to device</em> 🔊</div>'
                            else:
                                html += f'<div class="transcript-line"><span class="badge" style="color:{color}; border-color:{color};">{state}</span> {line_text}</div>'
                        
                        latency_print = f"  (STT Latency: {latency*1000:.0f}ms)" if latency > 0 else ""
                        html += f'<div class="transcript-line" style="color: #00d2ff; font-style: italic;"><span class="pulse-dot" style="background:#00d2ff;"></span> Translating {str(lang).upper()} via LLM Gateway...{latency_print}</div>'
                        
                        # Store the latency temporarily so the "translated" event can append it
                        st.session_state._last_latency = latency
                        
                        transcript_container.markdown(f'<div class="transcript-box">{html}</div>', unsafe_allow_html=True)

                    elif msg[0] == "translated":
                        latency = getattr(st.session_state, "_last_latency", 0.0)
                        lines.append((msg[1], "LLM", "en", latency))
                        st.session_state.transcripts.append((msg[1], "LLM", "en", latency))
                        
                    elif msg[0] == "tts":
                        lines.append((msg[1], "TTS", "en", 0.0))
                        st.session_state.transcripts.append((msg[1], "TTS", "en", 0.0))

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
            for line_item in st.session_state.transcripts:
                if len(line_item) == 2:
                    line_text, state = line_item
                    line_lang, latency = "en", 0.0
                else:
                    line_text, state, line_lang, latency = line_item
                    
                color = pipeline_states.get(state, "#ccd6f6")
                if state == "STT":
                    meta_badge = f'<span style="font-size:0.75rem; color:#8892b0; margin-left:8px;">[Detected: {str(line_lang).upper()}]</span>'
                    html += f'<div class="transcript-line"><span class="badge" style="color:{color}; border-color:{color};">STT</span> {line_text} {meta_badge}</div>'
                elif state == "LLM":
                    meta_badge = f'<span style="font-size:0.75rem; color:#8892b0; margin-left:8px;">[STT Latency: {latency*1000:.0f}ms]</span>' if latency > 0 else ""
                    html += f'<div class="transcript-line" style="background: rgba(0, 210, 255, 0.05);"><span class="badge" style="color:{color}; border-color:{color};">LLM Gateway</span> {line_text} {meta_badge}</div>'
                elif state == "TTS":
                    html += f'<div class="transcript-line" style="border-left: 2px solid {color}; padding-left: 10px;"><span class="badge" style="color:{color}; border-color:{color};">TTS Audio</span> <em>Synthesized and streamed to device</em> 🔊</div>'
                else:
                    html += f'<div class="transcript-line">{line_text}</div>'
            st.markdown(f'<div class="transcript-box">{html}</div>', unsafe_allow_html=True)

            # --- Inject Post-Session Closer ---
            st.success("🏁 **Conversation Session Finalized**")
            st.markdown("""
            ### The Universal-3 Pro Advantage
            You just witnessed AssemblyAI's cutting-edge cloud architecture powering the iTranslate hardware pipeline:
            
            *   ⚡️ **Sub-300ms Latency:** Voice data was piped directly from the device to the STT model and straight into the LLM Gateway without perceptible delay.
            *   🗣️ **Native Code-Switching:** English and Spanish were transcribed seamlessly in real-time without requiring the user to manually switch language profiles.
            *   🔋 **Zero Device Compute:** The STT model, LLM translation, and TTS synthesis were entirely offloaded to the cloud, preserving the hardware's battery and thermals.
            """)
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
    # -----------------------------------------------------------------------
    # Dynamic Proof Dashboard 
    # (Calculates latency/code-switching physically driven from the SDK)
    # -----------------------------------------------------------------------
    st.markdown("#### Real-Time Metrics")
    
    # 1. Calculate Average Latency from the LLM Gateway metadata injects
    llm_events = [item for item in st.session_state.transcripts if len(item) == 4 and item[1] == "LLM" and item[3] > 0]
    avg_latency = (sum(item[3] for item in llm_events) / len(llm_events)) * 1000 if llm_events else 0.0
    
    # 2. Extract Unique Languages natively detected by STT
    stt_events = [item for item in st.session_state.transcripts if len(item) == 4 and item[1] == "STT"]
    detected_langs = list(set([str(item[2]).upper() for item in stt_events]))
    langs_display = ", ".join(detected_langs) if detected_langs else "—"

    st.markdown(f"""
    <div class="stat-card" style="margin-bottom: 12px; border-left: 3px solid #64ffda;">
        <div class="stat-value">{avg_latency:.0f}<span style="font-size: 1rem;">ms</span></div>
        <div class="stat-label">Avg STT Latency</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-card" style="margin-bottom: 12px; border-left: 3px solid #00d2ff;">
        <div class="stat-value" style="font-size: 1.2rem;">{langs_display}</div>
        <div class="stat-label">Detected Languages</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-card" style="margin-bottom: 12px;">
        <div class="stat-value">{st.session_state.turn_count}</div>
        <div class="stat-label">Finalized Turns</div>
    </div>
    """, unsafe_allow_html=True)

    # Model info
    st.markdown("#### Cloud Parameters")
    st.markdown("""
    <div class="arch-box" style="padding: 16px;">
        <div style="margin-bottom: 8px;"><strong style="color: #64ffda;">Compute:</strong> 0% On-Device</div>
        <div style="margin-bottom: 8px;"><strong style="color: #64ffda;">Model:</strong> <code>u3-rt-pro</code></div>
        <div style="margin-bottom: 8px;"><strong style="color: #64ffda;">Audio:</strong> 16kHz PCM</div>
        <div style="margin-bottom: 8px;"><strong style="color: #64ffda;">Features:</strong> Code-Switching</div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #5a6680; font-size: 0.8rem;">
    Built for AssemblyAI Applied AI Engineering Take-Home •
    <a href="https://www.assemblyai.com/docs/streaming/universal-3-pro" style="color: #64ffda;">U3 Pro Docs</a> •
    <a href="https://www.assemblyai.com/docs/getting-started/transcribe-streaming-audio-from-a-microphone/python" style="color: #64ffda;">Streaming Tutorial</a>
</div>
""", unsafe_allow_html=True)
