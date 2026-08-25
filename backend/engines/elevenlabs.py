import os
import requests
from typing import Dict, Any
from .base import TTSEngine

class ElevenLabsEngine(TTSEngine):
    def capabilities(self) -> Dict[str, bool]:
        return {
            "stability": True,
            "similarity": True,
            "style": True,
            "speed": False, # ElevenLabs controls speed via pacing in text or some models, but v2 has style, similarity, stability. Wait, let's just stick to standard.
            "pitch": False,
            "volume": False,
            "speaker_boost": True
        }

    def generate(self, text: str, voice_profile: Dict[str, Any], settings: Dict[str, Any], language: str, output_path: str) -> bool:
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            print("ElevenLabs API key missing.")
            return False
            
        print(f"[ElevenLabsEngine] Generating text: {text[:30]}...")
        voice_id = voice_profile.get("engine_voice_id", "21m00Tcm4TlvDq8ikWAM")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": settings.get("stability", 0.5),
                "similarity_boost": settings.get("similarity", 0.75),
                "style": settings.get("style", 0.0),
                "use_speaker_boost": True
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
            else:
                print(f"[ElevenLabsEngine] API Error {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"[ElevenLabsEngine] Request failed: {e}")
            return False
