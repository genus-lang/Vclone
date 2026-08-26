"""
Per-Chunk Quality Evaluator
============================
After XTTS generates each audio chunk, this runs a fast QA pass.
If a chunk fails, the caller can regenerate it once.

Checks:
  1. Clipping detection
  2. Duration sanity (generated audio vs text length estimate)
  3. Volume consistency vs reference level
  4. Silence ratio (chunk that is mostly silence = failed generation)

Future (when ASR is available in venv):
  5. ASR text match vs expected text
  6. Speaker similarity vs reference embedding
"""
import os
import numpy as np
import librosa
from typing import Dict, Any, Optional

# Characters-per-second estimate for Hindi/English (XTTS typical)
CHARS_PER_SECOND_MIN = 5.0   # Very slow speech
CHARS_PER_SECOND_MAX = 25.0  # Very fast speech

class ChunkEvaluator:

    def evaluate(
        self,
        audio_path: str,
        text: str,
        reference_rms: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a generated audio chunk.

        Args:
            audio_path: Path to the generated WAV file
            text: The text that was used to generate this chunk
            reference_rms: Average RMS of previous chunks (for consistency check)

        Returns dict with:
            passed: bool
            issues: list of issue strings
            metrics: dict of measured values
        """
        issues = []
        metrics = {}

        if not os.path.exists(audio_path):
            return {"passed": False, "issues": ["File not found"], "metrics": {}}

        try:
            y, sr = librosa.load(audio_path, sr=None)
        except Exception as e:
            return {"passed": False, "issues": [f"Load failed: {e}"], "metrics": {}}

        duration = len(y) / sr
        metrics["duration_sec"] = round(duration, 2)

        # --- 1. Clipping ---
        clipping_ratio = float(np.sum(np.abs(y) >= 0.99) / len(y))
        metrics["clipping_ratio"] = round(clipping_ratio, 4)
        if clipping_ratio > 0.002:
            issues.append(f"Clipping detected ({clipping_ratio*100:.1f}%)")

        # --- 2. Duration sanity ---
        char_count = len(text.strip())
        min_expected = char_count / CHARS_PER_SECOND_MAX
        max_expected = char_count / CHARS_PER_SECOND_MIN
        metrics["expected_range_sec"] = (round(min_expected, 1), round(max_expected, 1))

        if duration < 0.3:
            issues.append("Audio too short — possible generation failure")
        elif duration < min_expected * 0.3:
            issues.append(f"Audio too short for text length (got {duration:.1f}s, expected {min_expected:.1f}s+)")
        elif duration > max_expected * 2.0:
            issues.append(f"Audio too long for text length (got {duration:.1f}s, expected max {max_expected:.1f}s)")

        # --- 3. Silence ratio ---
        non_silent = librosa.effects.split(y, top_db=30)
        speech_samples = sum(end - start for start, end in non_silent) if len(non_silent) > 0 else 0
        silence_ratio = 1.0 - (speech_samples / len(y))
        metrics["silence_ratio"] = round(silence_ratio, 3)
        if silence_ratio > 0.6:
            issues.append(f"Mostly silence ({silence_ratio*100:.0f}%) — possible generation failure")

        # --- 4. Volume consistency ---
        rms = float(np.sqrt(np.mean(y**2)))
        metrics["rms"] = round(rms, 5)
        if reference_rms is not None and reference_rms > 0:
            rms_ratio = rms / reference_rms
            metrics["rms_ratio"] = round(rms_ratio, 2)
            if rms_ratio < 0.2:
                issues.append(f"Volume too low vs other chunks (ratio {rms_ratio:.2f})")
            elif rms_ratio > 5.0:
                issues.append(f"Volume too high vs other chunks (ratio {rms_ratio:.2f})")

        passed = len(issues) == 0
        return {
            "passed": passed,
            "issues": issues,
            "metrics": metrics,
        }

    def get_rms(self, audio_path: str) -> float:
        """Quick RMS extraction for tracking consistency across chunks."""
        try:
            y, _ = librosa.load(audio_path, sr=None)
            return float(np.sqrt(np.mean(y**2)))
        except:
            return 0.0


chunk_evaluator = ChunkEvaluator()
