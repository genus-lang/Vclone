import os
import subprocess
import requests
import json
import base64
from typing import Dict, Any

from tts_manager import TTSManager
from dotenv import load_dotenv

load_dotenv()

class TTSEngine:
    def generate(self, text: str, voice_profile: Dict[str, Any], language: str, output_path: str) -> bool:
        """
        Generates TTS and saves to output_path.
        Returns True if successful, False otherwise.
        """
        raise NotImplementedError

class SarvamEngine(TTSEngine):
    def generate(self, text: str, voice_profile: Dict[str, Any], language: str, output_path: str) -> bool:
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
        
        # Sarvam expects inputs array and specific language/speaker mappings
        speaker = voice_profile.get("engine_voice", "meera")
        
        payload = {
            "inputs": [text],
            "target_language_code": "hi-IN" if "hi" in language else "en-IN",
            "speaker": speaker,
            "pitch": 0,
            "pace": voice_profile.get("default_settings", {}).get("pace", 1.0),
            "loudness": 1.5,
            "speech_sample_rate": 24000,
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

class ElevenLabsEngine(TTSEngine):
    def generate(self, text: str, voice_profile: Dict[str, Any], language: str, output_path: str) -> bool:
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            print("ElevenLabs API key missing.")
            return False
            
        print(f"[ElevenLabsEngine] Generating text: {text[:30]}...")
        voice_id = voice_profile.get("engine_voice", "21m00Tcm4TlvDq8ikWAM")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
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

class EdgeTTSEngine(TTSEngine):
    def generate(self, text: str, voice_profile: Dict[str, Any], language: str, output_path: str) -> bool:
        print(f"[EdgeTTSEngine] Generating fallback for {voice_profile['id']}")
        
        # Extract edge fallback voice ID
        # If the profile defines edge_voice, use it, else generic based on gender/lang
        edge_voice = voice_profile.get("edge_voice")
        if not edge_voice:
            if "hi" in language:
                edge_voice = "hi-IN-MadhurNeural" if voice_profile.get("gender") == "male" else "hi-IN-SwaraNeural"
            else:
                edge_voice = "en-US-GuyNeural" if voice_profile.get("gender") == "male" else "en-US-AriaNeural"
                
        cmd = ["edge-tts", "--voice", edge_voice, "-t", text, "--write-media", output_path]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[EdgeTTSEngine] subprocess failed: {e}")
            return False

class XTTSLocalEngine(TTSEngine):
    def __init__(self):
        self.tts_manager = TTSManager()
        
    def generate(self, text: str, voice_profile: Dict[str, Any], language: str, output_path: str) -> bool:
        safe_text = text[:30].encode('ascii', 'replace').decode('ascii')
        print(f"[XTTSLocalEngine] Generating text: {safe_text}...")
        # engine_voice is the reference speaker ID in XTTS
        speaker = voice_profile.get("engine_voice", "hero")
        speaker_wav = f"voices/{speaker}.wav"
        if not os.path.exists(speaker_wav):
            speaker_wav = "voices/narrator.wav"
            
        try:
            self.tts_manager.generate(text, speaker_wav, language, output_path)
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[XTTSLocalEngine] error: {e}")
            return False

class EngineManager:
    def __init__(self):
        self.engines = {
            "sarvam": SarvamEngine(),
            "elevenlabs": ElevenLabsEngine(),
            "edge": EdgeTTSEngine(),
            "xtts": XTTSLocalEngine()
        }
        self.registry_file = "voices.json"
        self.voice_registry = self.load_registry()

    def load_registry(self) -> Dict[str, Any]:
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading voice registry: {e}")
        return {}

    def save_registry(self):
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(self.voice_registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving voice registry: {e}")

    def add_voice(self, profile: Dict[str, Any]):
        self.voice_registry[profile["id"]] = profile
        self.save_registry()

    def delete_voice(self, voice_id: str):
        if voice_id in self.voice_registry:
            del self.voice_registry[voice_id]
            self.save_registry()
            return True
        return False

    def get_available_voices(self, language=None):
        voices = []
        for v_id, meta in self.voice_registry.items():
            # Support the frontend structure directly
            voices.append({
                "id": meta["id"],
                "name": meta["name"],
                "languages": [lang.split('-')[0] for lang in meta["languages"]], # simplify for UI 'hi', 'en'
                "gender": meta["gender"],
                "styles": meta["styles"],
                "tags": meta["tags"],
                "preview": meta["preview"],
                "engine": meta["engine"],
                "production": True, # All treated as production now
                "fallback": False
            })
        return voices

    def generate(self, text: str, voice_id: str, language: str, output_path: str):
        if voice_id not in self.voice_registry:
            raise ValueError(f"Voice {voice_id} not found in registry")
            
        profile = self.voice_registry[voice_id]
        engine_name = profile["engine"]
        
        # Try primary engine
        success = False
        if engine_name in self.engines:
            success = self.engines[engine_name].generate(text, profile, language, output_path)
            
        # Try fallback engine if primary fails
        if not success:
            fallback = profile.get("fallback_engine")
            print(f"Primary engine {engine_name} failed. Falling back to {fallback}...")
            if fallback in self.engines:
                success = self.engines[fallback].generate(text, profile, language, output_path)
                
        if not success:
            raise Exception("All engines failed to generate audio.")

engine_manager = EngineManager()
