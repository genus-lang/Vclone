import os
from typing import Dict, Any
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Voice, VoiceSettings
from .base import TTSEngine
from .sarvam import SarvamEngine
from .elevenlabs import ElevenLabsEngine
from .xtts import XTTSLocalEngine
from .edge import EdgeTTSEngine

class EngineManager:
    def __init__(self):
        self.engines: Dict[str, TTSEngine] = {
            "sarvam": SarvamEngine(),
            "elevenlabs": ElevenLabsEngine(),
            "edge": EdgeTTSEngine(),
            "xtts": XTTSLocalEngine()
        }

    def get_available_voices(self) -> list:
        db = SessionLocal()
        try:
            voices = db.query(Voice).all()
            result = []
            for v in voices:
                # Get capabilities from engine
                caps = {}
                if v.engine in self.engines:
                    caps = self.engines[v.engine].capabilities()
                
                result.append({
                    "id": v.id,
                    "name": v.name,
                    "languages": [v.language.split('-')[0]] if v.language else ["hi", "en"],
                    "gender": "unknown", # default
                    "styles": [],
                    "tags": [],
                    "preview": f"/v1/audio/previews/{v.id}.mp3",
                    "engine": v.engine,
                    "is_cloned": v.is_cloned,
                    "production": True,
                    "capabilities": caps
                })
            return result
        finally:
            db.close()

    def generate(self, text: str, voice_id: str, language: str, output_path: str, override_settings: Dict[str, Any] = None):
        db = SessionLocal()
        try:
            voice = db.query(Voice).filter(Voice.id == voice_id).first()
            if not voice:
                raise ValueError(f"Voice {voice_id} not found in database")
                
            # Construct profile for backward compatibility with engines
            profile = {
                "id": voice.id,
                "engine_voice_id": voice.engine_voice_id,
                "gender": "unknown", # Need to fix gender later if needed
                "fallback_engine": "edge" if voice.engine != "edge" else None
            }
            
            # Use override settings (from Preview) or load from DB
            settings_dict = override_settings
            if not settings_dict:
                settings = db.query(VoiceSettings).filter(VoiceSettings.voice_id == voice_id).first()
                if settings:
                    settings_dict = {
                        "stability": settings.stability,
                        "similarity": settings.similarity,
                        "expressiveness": settings.expressiveness,
                        "speed": settings.speed,
                        "pitch": settings.pitch,
                        "energy": settings.energy,
                        "warmth": settings.warmth,
                        "clarity": settings.clarity,
                        "resonance": settings.resonance,
                        "breathiness": settings.breathiness,
                        "pause_length": settings.pause_length,
                        "emphasis": settings.emphasis,
                        "emotion": settings.emotion,
                    }
                else:
                    settings_dict = {}

            # Try primary engine
            success = False
            engine_name = voice.engine
            if engine_name in self.engines:
                success = self.engines[engine_name].generate(text, profile, settings_dict, language, output_path)
                
            # Try fallback engine
            if not success:
                fallback = profile.get("fallback_engine")
                print(f"Primary engine {engine_name} failed. Falling back to {fallback}...")
                if fallback in self.engines:
                    success = self.engines[fallback].generate(text, profile, settings_dict, language, output_path)
                    
            if not success:
                raise Exception("All engines failed to generate audio.")
        finally:
            db.close()

engine_manager = EngineManager()
