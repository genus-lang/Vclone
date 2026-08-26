"""
Emotion & Style Detector
========================
Rule-based classifier that analyzes text chunks and returns emotion/style tags.
No ML models required — uses punctuation, keyword lists, and sentence structure.
These tags feed into:
  - Reference selection (dramatic text -> dramatic reference)
  - Pause calibration (angry text -> shorter pauses, dramatic -> longer)
  - Style hints for XTTS generation parameters
"""
import re
from typing import Dict, Any, List

# Hindi/English keyword banks
ANGRY_HI = ["रुको", "बंद करो", "चुप", "नहीं", "छोड़ो", "जाओ", "मत", "कभी नहीं", "धोखेबाज", "झूठा"]
ANGRY_EN = ["stop", "never", "liar", "traitor", "enough", "shut up", "get out", "how dare", "idiot"]
FEAR_HI = ["डर", "भाग", "बचाओ", "मदद", "खतरा", "सावधान", "सुनो", "वो", "वह"]
FEAR_EN = ["help", "run", "danger", "scared", "terrified", "please", "save", "watch out", "careful"]
SAD_HI = ["माफ", "अलविदा", "अफसोस", "रोना", "दुख", "याद", "भूल", "खो", "गया", "नहीं रहा"]
SAD_EN = ["sorry", "goodbye", "miss", "lost", "gone", "tears", "cry", "grief", "mourn", "farewell"]
HAPPY_HI = ["खुश", "बढ़िया", "शानदार", "जीत", "सफल", "मुबारक", "धन्यवाद", "प्यार", "अच्छा"]
HAPPY_EN = ["wonderful", "great", "love", "happy", "celebrate", "joy", "excellent", "perfect", "amazing"]
WHISPER_EN = ["quietly", "whispered", "murmured", "hushed", "softly said", "breathed"]
WHISPER_HI = ["धीरे", "फुसफुसाया", "चुपके", "हौले"]

# Style markers
DIALOGUE_PATTERN = re.compile(r'^["\'""''«»]|^"')
NARRATOR_KEYWORDS = ["meanwhile", "suddenly", "slowly", "then", "as", "while", "the room", "the city",
                     "तभी", "इसी बीच", "अचानक", "धीरे-धीरे", "उस समय", "कमरे में", "शहर में", "फिर"]


class EmotionDetector:
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze a text chunk and return emotion/style metadata.
        Returns:
          emotion: neutral | angry | fear | happy | sad | calm | dramatic
          style:   narration | dialogue | dramatic | whisper | exclamation
          energy:  0.0–1.0 (how intense the delivery should be)
          emphasis_words: list of words that should receive emphasis
          pause_multiplier: scaling factor for pauses (1.0 = normal)
        """
        text_lower = text.lower()
        words = text_lower.split()

        # --- Style detection (highest priority) ---
        style = "narration"
        if DIALOGUE_PATTERN.match(text.strip()):
            style = "dialogue"
        if any(w in text_lower for w in WHISPER_EN + WHISPER_HI):
            style = "whisper"

        # --- Punctuation signals ---
        excl_count = text.count("!")
        quest_count = text.count("?")
        ellipsis_count = text.count("…") + text.count("...")

        if excl_count >= 2 or (excl_count >= 1 and quest_count >= 1):
            style = "exclamation"

        # --- Emotion detection ---
        emotion = "neutral"
        energy = 0.45  # Default calm narration energy

        # Check keyword banks
        def _match(bank: List[str]) -> int:
            return sum(1 for kw in bank if kw in text_lower)

        angry_score = _match(ANGRY_HI) + _match(ANGRY_EN) + excl_count * 2
        fear_score  = _match(FEAR_HI) + _match(FEAR_EN) + excl_count
        sad_score   = _match(SAD_HI) + _match(SAD_EN)
        happy_score = _match(HAPPY_HI) + _match(HAPPY_EN)
        whisper_score = _match(WHISPER_HI) + _match(WHISPER_EN)

        scores = {
            "angry": angry_score,
            "fear":  fear_score,
            "sad":   sad_score,
            "happy": happy_score,
        }
        top_emotion = max(scores, key=scores.get)
        top_score = scores[top_emotion]

        if top_score >= 2:
            emotion = top_emotion

        # Ellipsis → dramatic/mysterious
        if ellipsis_count >= 1 and emotion == "neutral":
            emotion = "dramatic"

        # Whisper override
        if whisper_score >= 1:
            emotion = "calm"
            style = "whisper"

        # --- Energy mapping ---
        energy_map = {
            "angry":   0.85,
            "fear":    0.75,
            "happy":   0.70,
            "sad":     0.30,
            "dramatic":0.55,
            "calm":    0.25,
            "neutral": 0.45,
        }
        energy = energy_map.get(emotion, 0.45)
        # Boost energy slightly for exclamation style
        if excl_count >= 1:
            energy = min(1.0, energy + 0.1)

        # --- Emphasis words (capitalized words or words after !) ---
        emphasis_words = []
        for word in text.split():
            clean = re.sub(r'[^\w]', '', word)
            if clean.isupper() and len(clean) > 2:
                emphasis_words.append(clean)
        # Also mark words after "!"
        parts = text.split("!")
        for part in parts[:-1]:
            last_word = part.strip().split()[-1] if part.strip().split() else None
            if last_word:
                emphasis_words.append(re.sub(r'[^\w]', '', last_word))

        # --- Pause multiplier ---
        pause_map = {
            "angry":    0.6,   # Fast, urgent
            "fear":     0.7,
            "happy":    0.9,
            "sad":      1.4,   # Slow, heavy
            "dramatic": 1.6,   # Long, weighted pauses
            "calm":     1.2,
            "neutral":  1.0,
        }
        pause_multiplier = pause_map.get(emotion, 1.0)
        if style == "whisper":
            pause_multiplier *= 1.3

        return {
            "emotion": emotion,
            "style": style,
            "energy": round(energy, 2),
            "emphasis_words": list(set(emphasis_words)),
            "pause_multiplier": round(pause_multiplier, 2),
            "excl_count": excl_count,
            "quest_count": quest_count,
        }

    def best_reference_style(self, emotion: str, style: str) -> str:
        """Map emotion+style to a VoiceProfile name for reference selection."""
        if style in ("whisper", "calm") or emotion in ("sad", "calm"):
            return "Natural"
        if emotion in ("angry", "fear") or style == "exclamation":
            return "Dramatic"
        if style == "dialogue":
            return "Natural"
        return "Natural"  # Narrator default



    def analyze_with_confidence(self, text: str) -> Dict[str, Any]:
        """
        Like analyze(), but adds a confidence score (0.0-1.0).
        Confidence reflects how many signals agree on the detected emotion.
        Low confidence means the system is guessing — caller should allow override.
        """
        result = self.analyze(text)
        # Count how many signals contributed to emotion decision
        signals = 0
        total = 0

        excl_count = result["excl_count"]
        quest_count = result["quest_count"]
        emotion = result["emotion"]

        total = 3  # punctuation, keyword match, style
        if excl_count >= 1 or quest_count >= 1:
            signals += 1
        if emotion != "neutral":
            signals += 1
        if result["style"] != "narration":
            signals += 1

        confidence = round(signals / total, 2) if total > 0 else 0.5
        # If neutral with no signals, that's actually high confidence
        if emotion == "neutral" and signals == 0:
            confidence = 0.8

        result["confidence"] = confidence
        return result


emotion_detector = EmotionDetector()

