import os
from dotenv import load_dotenv
import assemblyai as aai
from assemblyai.streaming import v3 as aai_stream
import time

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
aai.settings.api_key = os.environ.get("ASSEMBLYAI_API_KEY")

class DummyClient:
    def __init__(self):
        self.connected = False
        
    def run(self):
        def on_open(client, event):
            print("OPEN", event)
            self.connected = True
        
        def on_turn(client, event):
            print("TURN", event)

        def on_error(client, error):
            print("ERROR", error)
            
        def on_close(client, event):
            print("CLOSE", event)

        client = aai_stream.StreamingClient(
            aai_stream.StreamingClientOptions(
                api_key=aai.settings.api_key,
                api_host="streaming.assemblyai.com",
            )
        )

        client.on(aai_stream.StreamingEvents.Begin, on_open)
        client.on(aai_stream.StreamingEvents.Turn, on_turn)
        client.on(aai_stream.StreamingEvents.Error, on_error)
        client.on(aai_stream.StreamingEvents.Termination, on_close)

        client.connect(
            aai_stream.StreamingParameters(
                speech_model="u3-rt-pro",
                sample_rate=16000,
                disable_formatting=True,
            )
        )
        print("Connected!")
        # just stream nothing to keep alive
        def empty():
            yield b'\x00' * 3200
            
        client.stream(empty())

if __name__ == "__main__":
    DummyClient().run()
