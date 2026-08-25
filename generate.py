import os
import glob

# Ensure FFmpeg is in PATH before anything else
ffmpeg_dirs = glob.glob(os.path.join(os.path.dirname(__file__), "ffmpeg-*-shared", "bin"))
if ffmpeg_dirs:
    os.environ["PATH"] = ffmpeg_dirs[0] + os.pathsep + os.environ.get("PATH", "")
    try:
        os.add_dll_directory(ffmpeg_dirs[0])
    except AttributeError:
        pass

import torch
from TTS.api import TTS

print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

device = "cuda" if torch.cuda.is_available() else "cpu"

tts = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    progress_bar=True
).to(device)

text = """
आज रात जंगल बिल्कुल शांत था।
लेकिन आरव को महसूस हो रहा था कि कोई उसका पीछा कर रहा है।

The moonlight disappeared behind the clouds,
and suddenly he heard a strange sound behind him.
"""

tts.tts_to_file(
    text=text,
    speaker_wav="voices/narrator.wav",
    language="hi",
    file_path="output/test.wav"
)

print("Done generating audio!")

if torch.cuda.is_available():
    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    print(f"VRAM Allocated: {allocated:.2f} GB")
    print(f"VRAM Reserved: {reserved:.2f} GB")

