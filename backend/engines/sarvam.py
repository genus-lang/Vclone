import os
import requests
import base64
from typing import Dict, Any
from .base import TTSEngine

class SarvamEngine(TTSEngine):
    def capabilities(self) -> Dict[str, bool]:
        # Sarvam Bulbul v3 supports pace.
        # It does NOT support pitch, volume, stability, or style natively via the V3 API.
        return {
            "stability": False,
            "similarity": False,
            "style": False,
            "speed": True, # mapped to pace
            "pitch": False,
            "volume": False,
            "speaker_boost": False
        }

    def generate(self, text: str, voice_profile: Dict[str, Any], settings: Dict[str, Any], language: str, output_path: str) -> bool:
        api_key = os.environ.get("SARVAM_API_KEY")
        if not api_key:
            print("Sarvam API key missing.")
            return False
            
        print(f"[SarvamEngine] Generating text: {text[:30]}...")
        url = "https://api.sarvam.ai/text-to-speech"
        
        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json"
        }
        
        speaker = voice_profile.get("engine_voice_id", "meera")
        
        payload = {
            "inputs": [text],
            "target_language_code": "hi-IN" if "hi" in language else "en-IN",
            "speaker": speaker,
            "pace": settings.get("speed", 1.0),
            "enable_preprocessing": True,
            "model": "bulbul:v3"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if "audios" in data and len(data["audios"]) > 0:
                    audio_b64 = data["audios"][0]
                    audio_bytes = base64.b64decode(audio_b64)
                    with open(output_path, "wb") as f:
                        f.write(audio_bytes)
                    return True
                else:
                    print(f"No audios in response: {data}")
                    return False
            else:
                print(f"[SarvamEngine] API Error {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"[SarvamEngine] Request failed: {e}")
            return False
