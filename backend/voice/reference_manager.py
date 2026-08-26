"""
Reference Manager
=================
Scores voice references on upload and auto-selects the best one per style.

Scoring Metrics (0-100):
  - SNR (signal-to-noise ratio)        — higher is better
  - Clipping                           — any clipping = major penalty
  - Speech density                     — % of audio that is actual speech
  - Silence ratio                      — % of audio that is silence
  - RMS consistency                    — how even/stable the volume is
  - Duration                           — ideal 10-25s
  - Peak level                         — should be -3 to -1 dBFS
  - Dynamic range                      — ideal >30 dB
  - Sample rate                        — 22050+ preferred

Style-based selection:
  - narration  → highest-scored reference with duration >= 12s
  - dialogue   → highest-scored short reference (natural rhythm)
  - dramatic   → any high-SNR reference
  - default    → overall best quality score
"""
import os
import numpy as np
import librosa
from typing import Dict, Any, Optional, List

class ReferenceManager:

    def score_reference(self, file_path: str) -> Dict[str, Any]:
        """
        Score a reference audio file on 9 metrics. Returns a full report dict.
        """
        try:
            y, sr = librosa.load(file_path, sr=None)
        except Exception as e:
            return self._empty_score(str(e))

        duration = len(y) / sr
        score = 100.0

        # --- 1. Clipping ---
        clipping_ratio = float(np.sum(np.abs(y) >= 0.99) / len(y))
        has_clipping = clipping_ratio > 0.001
        if has_clipping:
            score -= 35

        # --- 2. SNR estimate ---
        rms_frames = librosa.feature.rms(y=y)[0]
        sorted_rms = np.sort(rms_frames)
        noise_floor = float(np.mean(sorted_rms[:max(1, int(len(sorted_rms) * 0.05))]))
        signal_mean  = float(np.mean(sorted_rms[int(len(sorted_rms) * 0.5):]))
        snr_db = float(20 * np.log10((signal_mean + 1e-9) / (noise_floor + 1e-9)))
        snr_db = max(0.0, min(60.0, snr_db))
        # Penalize poor SNR: ideal >= 25 dB
        if snr_db < 10:
            score -= 25
        elif snr_db < 20:
            score -= 10
        elif snr_db < 25:
            score -= 5

        # --- 3. Speech density + silence ratio ---
        non_silent = librosa.effects.split(y, top_db=25)
        speech_samples = sum(end - start for start, end in non_silent)
        speech_density = float(speech_samples / len(y)) if len(y) > 0 else 0.0
        silence_ratio  = 1.0 - speech_density
        # Ideal: >70% speech
        if speech_density < 0.5:
            score -= 20
        elif speech_density < 0.7:
            score -= 8

        # --- 4. RMS consistency (std dev of RMS frames) ---
        rms_std = float(np.std(rms_frames))
        rms_mean = float(np.mean(rms_frames))
        rms_cv = rms_std / (rms_mean + 1e-9)  # coefficient of variation
        # High variation = uneven recording
        if rms_cv > 2.0:
            score -= 10
        elif rms_cv > 1.5:
            score -= 5

        # --- 5. Peak level ---
        peak_db = float(20 * np.log10(np.max(np.abs(y)) + 1e-9))
        # Ideal: -12 to -1 dBFS
        if peak_db < -24:
            score -= 15  # Too quiet
        elif peak_db < -18:
            score -= 8
        elif peak_db > -0.5:
            score -= 5   # Too loud / nearly clipping

        # --- 6. Dynamic range ---
        noise_floor_db = float(20 * np.log10(noise_floor + 1e-9))
        dynamic_range = peak_db - noise_floor_db
        if dynamic_range < 20:
            score -= 10
        elif dynamic_range < 30:
            score -= 5

        # --- 7. Duration penalty ---
        if duration < 3:
            score -= 30  # Too short for XTTS
        elif duration < 8:
            score -= 15
        elif duration > 60:
            score -= 5   # Too long to be a useful reference

        # --- 8. Sample rate ---
        if sr < 16000:
            score -= 15
        elif sr < 22050:
            score -= 5

        score = max(0, min(100, int(score)))

        return {
            "quality_score": score,
            "snr_db": round(snr_db, 1),
            "speech_density": round(speech_density, 3),
            "silence_ratio": round(silence_ratio, 3),
            "clipping_ratio": round(clipping_ratio, 4),
            "has_clipping": bool(has_clipping),
            "rms_consistency": round(1.0 - min(1.0, rms_cv / 2.0), 3),
            "peak_db": round(peak_db, 1),
            "dynamic_range_db": round(dynamic_range, 1),
            "duration_sec": round(duration, 2),
            "sample_rate": int(sr),
        }

    def _empty_score(self, error: str = "") -> Dict[str, Any]:
        return {
            "quality_score": 0, "snr_db": 0.0, "speech_density": 0.0,
            "silence_ratio": 1.0, "clipping_ratio": 0.0, "has_clipping": False,
            "rms_consistency": 0.0, "peak_db": -60.0, "dynamic_range_db": 0.0,
            "duration_sec": 0.0, "sample_rate": 0, "error": error
        }

    def select_best_reference(
        self,
        references: List[Dict[str, Any]],
        style: str = "narration",
    ) -> Optional[Dict[str, Any]]:
        """
        Auto-select the best reference for a given generation style.

        Each reference dict must have: file_path, quality_score, duration_sec, speech_density

        Style logic:
          narration  → duration >= 12s, highest quality_score
          dialogue   → any duration, highest speech_density (conversational)
          dramatic   → highest snr_db
          default    → overall highest quality_score
        """
        if not references:
            return None

        valid = [r for r in references if os.path.exists(r.get("file_path", ""))]
        if not valid:
            return None

        if style == "narration":
            candidates = [r for r in valid if r.get("duration_sec", 0) >= 12]
            if not candidates:
                candidates = valid  # Fallback
            return max(candidates, key=lambda r: r.get("quality_score", 0))

        if style == "dialogue":
            return max(valid, key=lambda r: r.get("speech_density", 0))

        if style == "dramatic":
            return max(valid, key=lambda r: r.get("snr_db", 0))

        # Default: best quality score
        return max(valid, key=lambda r: r.get("quality_score", 0))

    def grade_label(self, score: int) -> str:
        if score >= 85: return "Excellent"
        if score >= 70: return "Good"
        if score >= 50: return "Fair"
        return "Poor"


reference_manager = ReferenceManager()
