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

class AssemblyAIStreamer:
    """
    Handles the AssemblyAI Universal-3 Pro real-time websocket connection,
    as well as triggering the simulated downstream LLM Translation and TTS pipelines.
    """
    def __init__(self, api_key: str, transcript_queue: queue.Queue, error_queue: queue.Queue):
        self.api_key = api_key
        self.transcript_queue = transcript_queue
        self.error_queue = error_queue
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
                
            lang = getattr(event, 'language_code', 'en')
            
            # Send the turn structure with dynamic metadata
            self.transcript_queue.put(("turn", event.transcript, event.end_of_turn, lang))
            
            # If this turn is finalized, trigger the simulated LLM Gateway pipeline
            if event.end_of_turn and event.transcript.strip():
                calc_latency = (time.time() - self.turn_start_time) if self.turn_start_time else 0.0
                
                self.transcript_queue.put(("translating", "", lang, calc_latency))
                time.sleep(0.4) # Simulate LLM Gateway API call
                
                # Mock translation for demo UI based on what language AAI just detected
                target_lang = "EN" if str(lang).lower().startswith("es") else "ES"
                
                # Visually translate common phrases for a compelling demo
                t_lower = event.transcript.lower()
                translated_text = event.transcript
                
                if target_lang == "EN":
                    if "dónde" in t_lower or "donde" in t_lower: translated_text = "Where are you from?"
                    elif "qué pasa" in t_lower or "que pasa" in t_lower: translated_text = "What's up, friend?"
                    elif "bien" in t_lower: translated_text = "Yes, very good."
                    else: translated_text = f"(Translated from ES) {event.transcript}"
                else:
                    if "doing good" in t_lower or "how are you" in t_lower: translated_text = "Estoy bien. ¿Y tú cómo estás?"
                    elif "thank you" in t_lower: translated_text = "Muy bien, muchas gracias."
                    elif "hello" in t_lower: translated_text = "Hola."
                    else: translated_text = f"(Translated from EN) {event.transcript}"
                    
                mock_translation = f"[{target_lang}] {translated_text}" 
                
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

            # Following best practices: optimize latency and enable code-switching metadata
            self.client.connect(
                StreamingParameters(
                    speech_model="u3-rt-pro",
                    sample_rate=16000,
                    enable_language_identification=True, # Critical for Code-Switching demo
                    disable_formatting=True # Trade formatting for latency in live translations
                )
            )

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

