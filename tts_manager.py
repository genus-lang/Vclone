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

class TTSManager:
    def __init__(self):
        self.model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts = None
        self.is_loaded = False

    def load_model(self):
        if not self.is_loaded:
            print(f"Loading TTS Model to {self.device}...")
            self.tts = TTS(
                model_name=self.model_name,
                progress_bar=False
            ).to(self.device)
            self.is_loaded = True
            print("Model loaded successfully.")

    def generate(self, text: str, speaker_wav: str | list, language: str, output_path: str):
        if not self.is_loaded:
            self.load_model()
            
        safe_text = text[:30].encode('ascii', 'replace').decode('ascii')
        print(f"Generating audio for: {safe_text}...")
        self.tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path=output_path
        )
        return output_path

# Singleton instance
tts_manager = TTSManager()
