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

    def run_stream(self):
        def on_begin(client, event: BeginEvent):
            self.transcript_queue.put(("status", f"Session started: {event.id}"))

        def on_turn(client, event: TurnEvent):
            self.transcript_queue.put(("turn", event.transcript, event.end_of_turn))
            
            # If this turn is finalized, trigger the simulated LLM Gateway pipeline
            if event.end_of_turn and event.transcript.strip():
                self.transcript_queue.put(("translating", ""))
                time.sleep(0.4) # Simulate LLM Gateway API call
                mock_translation = f"[ES] {event.transcript}" # Mock translation for demo UI
                self.transcript_queue.put(("translated", mock_translation))
                
                time.sleep(0.3) # Simulate TTS Synthesis API call
                self.transcript_queue.put(("tts", "Audio ready"))

        def on_terminated(client, event: TerminationEvent):
            self.transcript_queue.put(("terminated", f"{event.audio_duration_seconds:.1f}s processed"))

        def on_error(client, error: StreamingError):
            self.error_queue.put(str(error))

        try:
            client = StreamingClient(
                StreamingClientOptions(
                    api_key=self.api_key,
                    api_host="streaming.assemblyai.com",
                )
            )
            client.on(StreamingEvents.Begin, on_begin)
            client.on(StreamingEvents.Turn, on_turn)
            client.on(StreamingEvents.Termination, on_terminated)
            client.on(StreamingEvents.Error, on_error)

            # Following best practices: optimize latency
            client.connect(
                StreamingParameters(
                    speech_model="u3-rt-pro",
                    sample_rate=16000,
                    disable_formatting=True # Trade formatting for latency in live translations
                )
            )

            client.stream(
                aai.extras.MicrophoneStream(sample_rate=16000)
            )
        except Exception as e:
            self.error_queue.put(str(e))

    def start_in_thread(self):
        """Starts the audio streaming in a background daemon thread."""
        stream_thread = threading.Thread(target=self.run_stream, daemon=True)
        stream_thread.start()
        return stream_thread
