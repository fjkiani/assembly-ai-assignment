import assemblyai as aai
from assemblyai.streaming.v3 import StreamingParameters

print("\n\n=== StreamingParameters Annotations ===")
for k, v in StreamingParameters.__annotations__.items():
    print(f"{k}: {v}")

