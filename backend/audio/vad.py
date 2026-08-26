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
            
            target_length = sr * 12 # 12 seconds max
            
            # Find intervals of non-silent regions (stricter threshold to avoid noise)
            intervals = librosa.effects.split(y, top_db=max(20, top_db))
            
            os.makedirs(output_dir, exist_ok=True)
            
            if len(intervals) == 0:
                # If everything is silence (or too quiet), just take the first 12s
                best_segment = y[:target_length]
            else:
                # Concatenate pure speech intervals to create a dense reference
                speech_chunks = []
                current_len = 0
                
                for interval in intervals:
                    start, end = interval
                    chunk = y[start:end]
                    
                    if current_len + len(chunk) > target_length:
                        needed = target_length - current_len
                        speech_chunks.append(chunk[:needed])
                        break
                    else:
                        speech_chunks.append(chunk)
                        current_len += len(chunk)
                        
                best_segment = np.concatenate(speech_chunks)
                
                # If we couldn't even find 3 seconds of speech, fallback to the original start
                if len(best_segment) < sr * 3:
                    first_start = intervals[0][0]
                    end_idx = min(first_start + target_length, len(y))
                    best_segment = y[first_start:end_idx]
            
            # ** CRITICAL FIX: Volume Normalization **
            # XTTS relies heavily on the volume of the reference audio. 
            # If the reference is too quiet, XTTS tries to compensate, causing massive distortion, 
            # metallic artifacts, and poor voice matching. We peak-normalize to 0.9.
            max_val = np.max(np.abs(best_segment))
            if max_val > 0.01: # Avoid dividing by zero or amplifying pure silence
                best_segment = best_segment * (0.9 / max_val)
                
            out_path = os.path.join(output_dir, "reference_optimal.wav")
            sf.write(out_path, best_segment, sr)
            
            return [out_path]
            
        except Exception as e:
            print(f"VAD segmentation failed: {e}")
            return [file_path] # Fallback to original

vad_processor = VoiceActivityDetector()
