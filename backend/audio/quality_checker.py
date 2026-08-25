import numpy as np
import librosa
import soundfile as sf
import os

class AudioCleaner:
    def analyze_quality(self, file_path: str):
        """
        Analyzes an audio file for noise floor, clipping, and silence.
        Returns a dictionary with quality metrics.
        """
        try:
            # Load audio
            y, sr = librosa.load(file_path, sr=None)
            
            # 1. Clipping detection
            # If any sample is exactly 1.0 or -1.0, it's clipping
            clipping_ratio = np.sum(np.abs(y) >= 0.99) / len(y)
            has_clipping = clipping_ratio > 0.001
            
            # 2. Noise floor estimation (using the quietest 5% of the audio)
            # Root mean square energy
            rms = librosa.feature.rms(y=y)[0]
            sorted_rms = np.sort(rms)
            noise_floor = np.mean(sorted_rms[:int(len(sorted_rms) * 0.05)])
            
            # 3. Dynamic range
            peak_db = 20 * np.log10(np.max(np.abs(y)) + 1e-6)
            noise_floor_db = 20 * np.log10(noise_floor + 1e-6)
            dynamic_range = peak_db - noise_floor_db
            
            # 4. RMS / Loudness
            rms_overall = np.sqrt(np.mean(y**2))
            rms_db = 20 * np.log10(rms_overall + 1e-6)
            
            # 5. Silence detection (leading/trailing)
            non_silent_intervals = librosa.effects.split(y, top_db=40)
            if len(non_silent_intervals) > 0:
                leading_silence_samples = non_silent_intervals[0][0]
                trailing_silence_samples = len(y) - non_silent_intervals[-1][1]
            else:
                leading_silence_samples = trailing_silence_samples = len(y)
                
            leading_silence_sec = leading_silence_samples / sr
            trailing_silence_sec = trailing_silence_samples / sr
            duration_sec = len(y) / sr
            
            # Score out of 100
            score = 100
            if has_clipping:
                score -= 40
            if dynamic_range < 30: # less than 30dB dynamic range is poor
                score -= (30 - dynamic_range) * 2
            
            return {
                "clipping_ratio": float(clipping_ratio),
                "has_clipping": bool(has_clipping),
                "peak_db": float(peak_db),
                "rms_db": float(rms_db),
                "dynamic_range_db": float(dynamic_range),
                "noise_floor_db": float(noise_floor_db),
                "leading_silence_sec": float(leading_silence_sec),
                "trailing_silence_sec": float(trailing_silence_sec),
                "duration_sec": float(duration_sec),
                "overall_score": max(0, min(100, int(score)))
            }
        except Exception as e:
            print(f"Error analyzing audio quality: {e}")
            return {
                "clipping_ratio": 0.0,
                "has_clipping": False,
                "peak_db": 0.0,
                "rms_db": 0.0,
                "dynamic_range_db": 0.0,
                "noise_floor_db": 0.0,
                "leading_silence_sec": 0.0,
                "trailing_silence_sec": 0.0,
                "duration_sec": 0.0,
                "overall_score": 0
            }

quality_checker = AudioCleaner()
