import librosa
import soundfile as sf
import os
import numpy as np

class VoiceActivityDetector:
    def segment_audio(self, file_path: str, output_dir: str, top_db: int = 30) -> list[str]:
        """
        Extracts a single, high-quality 10-12 second contiguous chunk of audio
        starting from the first non-silent speech. This preserves natural pacing
        and breathing, which is critical for Coqui XTTS zero-shot cloning.
        """
        try:
            y, sr = librosa.load(file_path, sr=None)
            
            # Find intervals of non-silent regions
            intervals = librosa.effects.split(y, top_db=top_db)
            
            if len(intervals) == 0:
                # If everything is silence (or too quiet), just return the original
                return [file_path]
                
            os.makedirs(output_dir, exist_ok=True)
            
            # Start from the beginning of the first actual speech
            first_speech_start = intervals[0][0]
            
            # Target exactly 12 seconds of contiguous audio (XTTS sweet spot is 6-12s)
            target_length = sr * 12
            
            # Slice out the contiguous block
            end_idx = min(first_speech_start + target_length, len(y))
            best_segment = y[first_speech_start:end_idx]
            
            # If the segment is extremely short (e.g., < 3 seconds), just use the whole file
            # to give the model as much data as possible
            if len(best_segment) < sr * 3:
                best_segment = y
            
            out_path = os.path.join(output_dir, "reference_optimal.wav")
            sf.write(out_path, best_segment, sr)
            
            return [out_path]
            
        except Exception as e:
            print(f"VAD segmentation failed: {e}")
            return [file_path] # Fallback to original

vad_processor = VoiceActivityDetector()
