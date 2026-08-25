import re

class TextNormalizer:
    def normalize(self, text: str, language: str = "hi") -> str:
        # Clean up whitespace but preserve paragraph breaks
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Replace non-standard characters while preserving punctuation
        # E.g. curly quotes to straight quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Remove Markdown and weird symbols that crash XTTS
        text = text.replace('\n', ' ')
        text = re.sub(r'[#*~_\[\]{}<>|\\^]+', '', text)
        text = text.replace('—', '-')
        
        # XTTS's underlying num2words library does not support Hindi (hi).
        # We must manually replace digits to prevent NotImplementedError crashes.
        if "hi" in language.lower():
            hindi_numbers = {
                '0': 'शून्य', '1': 'एक', '2': 'दो', '3': 'तीन', '4': 'चार',
                '5': 'पांच', '6': 'छह', '7': 'सात', '8': 'आठ', '9': 'नौ'
            }
            for digit, word in hindi_numbers.items():
                text = text.replace(digit, f" {word} ")
                
        # Keep essential punctuation: , . ! ? । (Hindi danda) -
        # The TTS engine handles these as prosody markers.
        return text.strip()

text_normalizer = TextNormalizer()
