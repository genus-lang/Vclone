import re
from .normalizer import text_normalizer
from .pronunciation import pronunciation_dict
from .prosody import prosody_processor

class TextAnalyzer:
    def detect_language(self, text: str) -> str:
        # Simple heuristic: presence of Devanagari block indicates Hindi
        if re.search(r'[\u0900-\u097F]', text):
            return "hi-IN"
        return "en-IN"

    def analyze(self, raw_text: str):
        """
        Runs the full text quality pipeline:
        Raw Text -> Normalization -> Pronunciation -> Segmentation
        Returns a dict of processed segments.
        """
        # 1. Detect Global Language
        lang = self.detect_language(raw_text)
        
        # 2. Normalize
        normalized = text_normalizer.normalize(raw_text, language=lang)
        
        # 3. Pronunciation Replacement (don't overwrite original_text reference)
        pronounced = pronunciation_dict.apply(normalized)
        
        # 4. Prosody / Sentence Segmentation
        segments = prosody_processor.segment(pronounced)
        
        return {
            "original_text": raw_text,
            "processed_text": pronounced,
            "language": lang,
            "segments": segments
        }

text_analyzer = TextAnalyzer()
