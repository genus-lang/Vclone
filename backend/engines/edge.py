import subprocess
from typing import Dict, Any
from .base import TTSEngine

class EdgeTTSEngine(TTSEngine):
    def capabilities(self) -> Dict[str, bool]:
        return {
            "stability": False,
            "similarity": False,
            "style": False,
            "speed": True, # EdgeTTS has --rate
            "pitch": True, # EdgeTTS has --pitch
            "volume": True, # EdgeTTS has --volume
            "speaker_boost": False
        }

    def generate(self, text: str, voice_profile: Dict[str, Any], settings: Dict[str, Any], language: str, output_path: str) -> bool:
        print(f"[EdgeTTSEngine] Generating fallback for {voice_profile.get('id')}")
        
        # Extract edge fallback voice ID
        edge_voice = voice_profile.get("edge_voice")
        if not edge_voice:
            if "hi" in language:
                edge_voice = "hi-IN-MadhurNeural" if voice_profile.get("gender") == "male" else "hi-IN-SwaraNeural"
            else:
                edge_voice = "en-US-GuyNeural" if voice_profile.get("gender") == "male" else "en-US-AriaNeural"
                
        cmd = ["edge-tts", "--voice", edge_voice, "-t", text]
        
        # Apply settings
        speed = settings.get("speed", 1.0)
        if speed != 1.0:
            # EdgeTTS format: +10% or -10%
            percent = int((speed - 1.0) * 100)
            sign = "+" if percent >= 0 else ""
            cmd.extend(["--rate", f"{sign}{percent}%"])
            
        pitch = settings.get("pitch", 0.0)
        if pitch != 0.0:
            sign = "+" if pitch >= 0 else ""
            cmd.extend(["--pitch", f"{sign}{int(pitch)}Hz"])
            
        volume = settings.get("volume", 1.0)
        if volume != 1.0:
            percent = int((volume - 1.0) * 100)
            sign = "+" if percent >= 0 else ""
            cmd.extend(["--volume", f"{sign}{percent}%"])
            
        cmd.extend(["--write-media", output_path])
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[EdgeTTSEngine] subprocess failed: {e}")
            return False
