import re

class LanguageDetector:
    def __init__(self):
        # Unicode range for Devanagari is \u0900-\u097F
        self.hindi_pattern = re.compile(r'[\u0900-\u097F]+')
        self.english_pattern = re.compile(r'[a-zA-Z]+')

    def detect_primary_language(self, text: str) -> str:
        """Detect the primary language of a block of text."""
        hindi_matches = len(self.hindi_pattern.findall(text))
        english_matches = len(self.english_pattern.findall(text))
        
        if hindi_matches >= english_matches:
            return "hi"
        return "en"

    def split_by_language(self, text: str):
        """
        Splits a mixed sentence into spans of homogenous languages.
        Returns a list of dicts: [{"text": "फू चिएन ने देखा कि ", "lang": "hi"}, {"text": "something was wrong", "lang": "en"}]
        """
        words = text.split()
        spans = []
        current_span = []
        current_lang = None
        
        for word in words:
            word_lang = "hi" if self.hindi_pattern.search(word) else "en"
            
            # If a word is just punctuation or numbers, attach it to the current language
            if not self.hindi_pattern.search(word) and not self.english_pattern.search(word):
                if current_lang:
                    word_lang = current_lang
                else:
                    word_lang = "hi" # Default
            
            if current_lang is None:
                current_lang = word_lang
                
            if word_lang == current_lang:
                current_span.append(word)
            else:
                spans.append({"text": " ".join(current_span), "lang": current_lang})
                current_span = [word]
                current_lang = word_lang
                
        if current_span:
            spans.append({"text": " ".join(current_span), "lang": current_lang})
            
        return spans

language_detector = LanguageDetector()
