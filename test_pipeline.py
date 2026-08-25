import sys
import os
sys.path.insert(0, '.')
os.environ["PYTHONUTF8"] = "1"

from backend.text.pipeline import text_pipeline

test = "VR device mein SAN Points 20 ka bonus tha. Fu Qian ne warehouse mein AI system dekha."
chunks = text_pipeline.process_chapter(test, "hi")
for chunk in chunks:
    try:
        print(chunk.encode("utf-8").decode("utf-8"))
    except:
        print("[unprintable chunk]")
