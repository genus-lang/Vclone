"""
Smart Pause Engine
==================
Generates calibrated silence durations (in seconds) between audio chunks
based on text context, punctuation, and emotion tags.

Instead of concatenating chunks with zero pause (robotic) or fixed pause
(unnatural), we compute context-aware pauses that match how a human narrator
would breathe and pace their delivery.

Usage:
  pause_sec = pause_engine.get_pause(text, position, emotion_tag, total_chunks)
  silence = pause_engine.generate_silence(pause_sec, sample_rate)
"""
import re
import numpy as np
from typing import Optional

class SmartPauseEngine:
    # Base pause durations in seconds
    BASE_PAUSES = {
        "comma":         0.12,   # Comma mid-sentence
        "sentence":      0.28,   # End of sentence (narration)
        "question":      0.35,   # End of question
        "exclamation":   0.20,   # End of exclamation (shorter — urgent)
        "dialogue_end":  0.40,   # After a dialogue line
        "paragraph":     0.55,   # Paragraph boundary
        "chapter":       1.20,   # Chapter break
        "ellipsis":      0.65,   # Dramatic pause (...)
        "default":       0.22,   # Fallback
    }

    def get_pause(
        self,
        text: str,
        position: int,
        total_chunks: int,
        emotion_data: Optional[dict] = None,
        is_paragraph_end: bool = False,
    ) -> float:
        """
        Calculate the pause duration AFTER this chunk.

        Args:
            text: The text chunk (already processed)
            position: Index of this chunk (0-based)
            total_chunks: Total number of chunks
            emotion_data: Output from EmotionDetector.analyze()
            is_paragraph_end: Whether this chunk ends a paragraph

        Returns:
            Pause duration in seconds
        """
        stripped = text.strip()
        pause_multiplier = 1.0

        if emotion_data:
            pause_multiplier = emotion_data.get("pause_multiplier", 1.0)

        # Last chunk — no trailing pause
        if position >= total_chunks - 1:
            return 0.0

        # Paragraph boundary
        if is_paragraph_end:
            base = self.BASE_PAUSES["paragraph"]
            return round(base * pause_multiplier, 3)

        # Detect ending character
        if not stripped:
            return self.BASE_PAUSES["default"]

        last_char = stripped[-1]

        if stripped.endswith("...") or stripped.endswith("…"):
            base = self.BASE_PAUSES["ellipsis"]
        elif last_char in ("!", "！"):
            base = self.BASE_PAUSES["exclamation"]
        elif last_char in ("?", "？"):
            base = self.BASE_PAUSES["question"]
        elif last_char in (".", "।", "。"):
            # Check if it's dialogue
            if emotion_data and emotion_data.get("style") == "dialogue":
                base = self.BASE_PAUSES["dialogue_end"]
            else:
                base = self.BASE_PAUSES["sentence"]
        elif last_char in (",", "،", "、"):
            base = self.BASE_PAUSES["comma"]
        else:
            base = self.BASE_PAUSES["default"]

        result = base * pause_multiplier

        # Hard clamp: never more than 2s, never less than 50ms
        result = max(0.05, min(2.0, result))
        return round(result, 3)

    def generate_silence(self, duration_sec: float, sample_rate: int = 24000, channels: int = 1) -> np.ndarray:
        """
        Generate a numpy array of silence (zeros) for the given duration.
        Returns shape (channels, samples) to match pedalboard/librosa format.
        """
        n_samples = int(duration_sec * sample_rate)
        if channels == 1:
            return np.zeros(n_samples, dtype=np.float32)
        return np.zeros((channels, n_samples), dtype=np.float32)

pause_engine = SmartPauseEngine()
