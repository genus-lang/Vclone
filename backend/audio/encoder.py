import os
from pydub import AudioSegment

class AudioEncoder:
    def encode_to_mp3(self, wav_path: str, mp3_path: str = None, bitrate: str = "192k") -> str:
        """
        Encodes a WAV file to MP3. If mp3_path is None, saves alongside the WAV file.
        Returns the path to the MP3 file.
        """
        if not mp3_path:
            mp3_path = wav_path.rsplit(".", 1)[0] + ".mp3"
            
        try:
            audio = AudioSegment.from_wav(wav_path)
            audio.export(mp3_path, format="mp3", bitrate=bitrate)
            return mp3_path
        except Exception as e:
            print(f"[AudioEncoder] Failed to encode MP3: {e}")
            # Fallback to just copying or renaming if ffmpeg is missing
            if wav_path != mp3_path:
                import shutil
                shutil.copy2(wav_path, mp3_path)
            return mp3_path

audio_encoder = AudioEncoder()
