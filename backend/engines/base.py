from typing import Dict, Any

class TTSEngine:
    def capabilities(self) -> Dict[str, bool]:
        """Return a dictionary defining which controls this engine supports NATIVELY."""
        return {
            "stability": False,
            "similarity": False,
            "style": False,
            "speed": False,
            "pitch": False,
            "volume": False,
            "speaker_boost": False,
            "temperature": False,
            "emotion": False
        }

    def generate(self, text: str, voice_profile: Dict[str, Any], settings: Dict[str, Any], language: str, output_path: str) -> bool:
        """
        Generates TTS and saves to output_path.
        Returns True if successful, False otherwise.
        """
        raise NotImplementedError
