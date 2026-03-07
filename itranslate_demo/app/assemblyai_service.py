# ==============================================================================
# ARCHITECTURE MAPPING: CLOUD ORCHESTRATION ENGINE (STT -> LLM -> TTS)
# ==============================================================================
# This file (`assemblyai_service.py`) represents the remote Cloud backend.
# It handles the heavy architectural lifting entirely off-device:
#   1. STT: Streams audio to AssemblyAI Universal-3 Pro via `u3-rt-pro` model.
#   2. LLM Gateway: Pipes finalized transcripts immediately into Cohere's Command AI.
#   3. TTS: Synthesizes the translation into audio (Simulated).
# ==============================================================================

import time
import queue
import threading
import assemblyai as aai
from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    TerminationEvent,
    TurnEvent,
)

# ================================================================
# SINGLE SOURCE OF TRUTH: Domain-specific keyterms for STT boosting.
# Imported by app.py for dynamic UI rendering — never hardcode these elsewhere.
# Per AssemblyAI's Keyterms Prompting docs:
#   - Max 100 keyterms per session, each ≤ 50 chars
#   - Word-level boosting during inference + turn-level post-processing
# ================================================================
DOMAIN_KEYTERMS = [
    # Brand names
    "iTranslate", "AssemblyAI", "EpiPen",
    # Clinician roles & context
    "primary care physician", "triage nurse",
    "attending physician", "on-call doctor",
    # Conditions (terms the model may fumble without boost)
    "hypertension", "type 2 diabetes",
    "shortness of breath", "epigastric pain",
    # Medications & doses (highest-value keyterms — unusual drug names)
    "ibuprofen 400 milligrams", "paracetamol 500 milligrams",
    "insulin glargine", "metformin", "amoxicillin",
    "epinephrine auto-injector", "acetaminophen",
    "metoprolol", "lisinopril",
]

class AssemblyAIStreamer:
    """
    Handles the AssemblyAI Universal-3 Pro real-time websocket connection,
    as well as triggering the simulated downstream LLM Translation and TTS pipelines.
    """
    def __init__(self, api_key: str, transcript_queue: queue.Queue, error_queue: queue.Queue, use_prompt: bool = True):
        self.api_key = api_key
        self.transcript_queue = transcript_queue
        self.error_queue = error_queue
        self.use_prompt = use_prompt
        self.is_streaming = False
        self.client = None
        self.audio_stream = None
        self.pyaudio_instance = None
        self.stream_thread = None
        self.turn_start_time = None

    def _setup_pyaudio(self):
        import pyaudio
        self.pyaudio_instance = pyaudio.PyAudio()
        self.audio_stream = self.pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=3200
        )

    def run_stream(self):
        def on_begin(client, event: BeginEvent):
            self.transcript_queue.put(("status", f"Session started: {event.id}"))

        def on_turn(client, event: TurnEvent):
            if self.turn_start_time is None and event.transcript.strip():
                self.turn_start_time = time.time()
                
            # Use None/unknown when language is not present on this event
            lang = getattr(event, "language_code", None)
            
            # Send the turn structure with dynamic metadata
            self.transcript_queue.put(("turn", event.transcript, event.end_of_turn, lang or "UNKNOWN"))
            
            # If this turn is finalized, trigger the simulated LLM Gateway pipeline
            if event.end_of_turn and event.transcript.strip():
                calc_latency = (time.time() - self.turn_start_time) if self.turn_start_time else 0.0
                
                self.transcript_queue.put(("translating", "", lang or "UNKNOWN", calc_latency))
                # Real translation via Cohere LLM (simulating the Gateway pattern)
                try:
                    import cohere
                    import os
                    
                    # Determine source → target based on detected language
                    lang_lower = lang.lower() if isinstance(lang, str) else ""
                    is_spanish = lang_lower.startswith("es")
                    is_italian = lang_lower.startswith("it")
                    is_french  = lang_lower.startswith("fr")
                    is_english = lang_lower.startswith("en")
                    
                    if is_spanish or is_italian or is_french:
                        target_lang = "EN"
                        prompt = f"Translate the following spoken phrase directly to English. Output ONLY the raw translation, no quotes or intro: '{event.transcript}'"
                    elif is_english:
                        target_lang = "ES"
                        prompt = f"Translate the following spoken phrase directly to Spanish. Output ONLY the raw translation, no quotes or intro: '{event.transcript}'"
                    else:
                        target_lang = "EN"
                        prompt = f"Identify the language and translate the following phrase directly to English. Output ONLY the raw translation: '{event.transcript}'"
                    
                    cohere_key = os.environ.get("COHERE_API_KEY")
                    if not cohere_key:
                        raise ValueError("COHERE_API_KEY missing")
                        
                    co = cohere.Client(cohere_key)
                    response = co.chat(
                        model="command-a-03-2025",
                        message=prompt,
                        temperature=0.3
                    )
                    translated_text = response.text.strip().strip('"')
                    
                    mock_translation = f"[{target_lang}] {translated_text}"
                except Exception as e:
                    # Graceful fallback if Cohere fails or key is missing
                    target_lang = "EN" if (isinstance(lang, str) and not lang.lower().startswith("en")) else "ES"
                    mock_translation = f"[{target_lang}] (Translated from {lang[:2].upper() if lang else 'UNKNOWN'}) {event.transcript}"
                
                self.transcript_queue.put(("translated", mock_translation))
                
                time.sleep(0.3) # Simulate TTS Synthesis API call
                self.transcript_queue.put(("tts", "Audio ready"))
                self.turn_start_time = None

        def on_terminated(client, event: TerminationEvent):
            self.transcript_queue.put(("terminated", f"{event.audio_duration_seconds:.1f}s processed"))

        def on_error(client, error: StreamingError):
            self.error_queue.put(str(error))

        try:
            self._setup_pyaudio()
            
            self.client = StreamingClient(
                StreamingClientOptions(
                    api_key=self.api_key,
                    api_host="streaming.assemblyai.com",
                )
            )
            self.client.on(StreamingEvents.Begin, on_begin)
            self.client.on(StreamingEvents.Turn, on_turn)
            self.client.on(StreamingEvents.Termination, on_terminated)
            self.client.on(StreamingEvents.Error, on_error)

            # ================================================================
            # UNIVERSAL-3 PRO: PROMPTING & KEYTERMS BOOSTING
            # ================================================================
            # Per AssemblyAI's Prompting Guide (https://assemblyai.com/docs/streaming/prompting):
            #   - `prompt` is INSTRUCTIONAL: controls punctuation, disfluencies, formatting.
            #     When omitted, a built-in default prompt delivers 88% turn detection accuracy.
            #   - `keyterms_prompt` is for DOMAIN-SPECIFIC TERM BOOSTING: biases the model
            #     at both word-level (during inference) and turn-level (post-processing).
            #   - `prompt` and `keyterms_prompt` CANNOT be used simultaneously.
            #
            # For iTranslate's use case, `keyterms_prompt` is the higher-value lever:
            #   it ensures brand names, medical terms, and multilingual phrases are
            #   recognized accurately — directly improving downstream translation quality.
            # ================================================================
            itranslate_keyterms = DOMAIN_KEYTERMS if self.use_prompt else None

            # Build connection parameters
            # `u3-rt-pro` is the Universal-3 Pro model name per official docs.
            # For U3-Pro, formatting is built into the turn detection system —
            # `end_of_turn` and `turn_is_formatted` always have the same value.
            connect_params = StreamingParameters(
                speech_model="u3-rt-pro",
                sample_rate=16000,
                language_detection=True,  # Critical for multilingual code-switching
            )
            
            # Conditionally inject keyterms (cannot coexist with `prompt`)
            if itranslate_keyterms:
                connect_params.keyterms_prompt = itranslate_keyterms

            self.client.connect(connect_params)

            # Feed the websocket incrementally via a generator
            def audio_source():
                while self.is_streaming and self.audio_stream:
                    try:
                        yield self.audio_stream.read(3200, exception_on_overflow=False)
                    except Exception:
                        break

            self.client.stream(audio_source())

        except Exception as e:
            self.error_queue.put(str(e))
        finally:
            self.stop()

    def start_in_thread(self):
        """Starts the audio streaming in a background daemon thread."""
        self.is_streaming = True
        self.stream_thread = threading.Thread(target=self.run_stream, daemon=True)
        self.stream_thread.start()
        return self.stream_thread

    def stop(self):
        """Cleanly releases the audio interface and websocket."""
        self.is_streaming = False
        try:
            if self.client:
                self.client.close()
        except: pass
        
        try:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
        except: pass

        self.client = None
        self.audio_stream = None
        self.pyaudio_instance = None

