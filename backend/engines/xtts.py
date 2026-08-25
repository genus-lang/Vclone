import os
import sys
from typing import Dict, Any
import torch
from .base import TTSEngine

# Resolve paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from tts_manager import TTSManager

class XTTSLocalEngine(TTSEngine):
    def __init__(self):
        self.tts_manager = TTSManager()
        
    def capabilities(self) -> Dict[str, bool]:
        # XTTS API `tts_to_file` can technically pass some controls, 
        # but realistically speed/pitch are very limited or require modifying the vocoder.
        # We will expose speed if we want to add an audio processor later, or native if it supports it.
        # For MVP, we expose speed.
        return {
            "stability": False,
            "similarity": False,
            "style": False,
            "speed": True, # Can be handled by ffmpeg post-processing or natively if added
            "pitch": True, # Same as speed
            "volume": False,
            "speaker_boost": False
        }

    def generate(self, text: str, voice_profile: Dict[str, Any], settings: Dict[str, Any], language: str, output_path: str) -> bool:
        safe_text = text[:30].encode('ascii', 'replace').decode('ascii')
        print(f"[XTTSLocalEngine] Generating text: {safe_text}...")
        
        # engine_voice is the reference speaker ID in XTTS
        speaker = voice_profile.get("engine_voice_id", "hero")
        
        # Resolve to original voices dir
        from backend.database import SessionLocal
        from backend.models import VoiceProfile, VoiceReference
        
        db = SessionLocal()
        speaker_wavs = []
        try:
            profile = db.query(VoiceProfile).filter(VoiceProfile.voice_id == speaker).first()
            if profile:
                refs = db.query(VoiceReference).filter(VoiceReference.profile_id == profile.id).all()
                speaker_wavs = [ref.file_path for ref in refs if os.path.exists(ref.file_path)]
        finally:
            db.close()
            
        if not speaker_wavs:
            speaker_wav_path = os.path.join(BASE_DIR, "voices", f"{speaker}.wav")
            if not os.path.exists(speaker_wav_path):
                speaker_wav_path = os.path.join(BASE_DIR, "voices", "narrator.wav")
            speaker_wavs = speaker_wav_path
            
        try:
            # For now, XTTSManager doesn't natively accept settings. 
            # We would apply speed/pitch via audio post-processing in `audio_processor.py`.
            self.tts_manager.generate(text, speaker_wavs, language, output_path)
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[XTTSLocalEngine] error: {e}")
            return False
