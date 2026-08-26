from backend.text.normalizer import text_normalizer
from backend.text.abbreviations import abbreviation_normalizer
from backend.text.numbers import number_normalizer
from backend.text.pronunciation import pronunciation_dict
from backend.text.language_detector import language_detector
from backend.text.g2p import g2p_processor
from backend.prosody.emotion import emotion_detector
import re

def split_into_sentences(text: str):
    sentences = re.split(r"([.!?|]+['\"]?\s*)", text)
    result = []
    for i in range(0, len(sentences) - 1, 2):
        chunk = (sentences[i] + sentences[i + 1]).strip()
        if chunk:
            result.append(chunk)
    if len(sentences) % 2 != 0 and sentences[-1].strip():
        result.append(sentences[-1].strip())
    return result

class TextPipeline:
    def process_chapter(self, text: str, target_lang: str = "hi"):
        """Process chapter text and return TTS-ready chunks."""
        # 1. Base normalization
        text = text_normalizer.normalize(text, target_lang)
        # 2. User pronunciation dictionary
        text = pronunciation_dict.apply(text)
        # 3. Abbreviations
        text = abbreviation_normalizer.normalize(text, target_lang)
        # 4. Numbers
        text = number_normalizer.normalize(text, target_lang)
        # 5. Sentence segmentation
        sentences = split_into_sentences(text)
        # 6. G2P — Hinglish token normalization
        g2p_sentences = []
        for s in sentences:
            try:
                g2p_sentences.append(g2p_processor.normalize_sentence(s, context_lang=target_lang))
            except Exception as e:
                print(f"[G2P] Error on sentence: {e}")
                g2p_sentences.append(s)
        # 7. Hard-constraint chunking
        final_chunks = []
        for sentence in g2p_sentences:
            if len(sentence) > 150:
                parts = sentence.split(",")
                for p in parts:
                    p = p.strip()
                    if not p:
                        continue
                    if len(p) > 150:
                        words = p.split()
                        cur, cur_len = [], 0
                        for w in words:
                            if cur_len + len(w) > 140:
                                final_chunks.append(" ".join(cur))
                                cur, cur_len = [w], len(w)
                            else:
                                cur.append(w)
                                cur_len += len(w) + 1
                        if cur:
                            final_chunks.append(" ".join(cur))
                    else:
                        final_chunks.append(p)
            else:
                final_chunks.append(sentence)
        return final_chunks

    def process_chapter_with_emotion(self, text: str, target_lang: str = "hi"):
        """
        Like process_chapter(), also returns emotion metadata per chunk.
        Returns list of dicts: {text, emotion}
        """
        chunks = self.process_chapter(text, target_lang)
        result = []
        for chunk in chunks:
            try:
                emotion = emotion_detector.analyze_with_confidence(chunk)
            except Exception as e:
                print(f"[Emotion] Failed: {e}")
                emotion = {"emotion": "neutral", "style": "narration", "energy": 0.45, "confidence": 0.5}
            result.append({"text": chunk, "emotion": emotion})
        return result

text_pipeline = TextPipeline()
