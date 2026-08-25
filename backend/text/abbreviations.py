import re

class AbbreviationNormalizer:
    def __init__(self):
        # Default common English abbreviations found in webnovels
        self.abbreviations = {
            "AI": "ए आई",
            "VR": "वी आर",
            "API": "ए पी आई",
            "SAN": "सैन",
            "HP": "एच पी",
            "MP": "एम पी",
            "EXP": "ई एक्स पी",
            "NPC": "एन पी सी",
            "CEO": "सी ई ओ"
        }

    def normalize(self, text: str, lang: str = "hi") -> str:
        if lang != "hi":
            return text
            
        for abbr, hindi_pronunciation in self.abbreviations.items():
            # Use word boundaries to ensure we don't replace "SAN" inside "SAND"
            text = re.sub(rf'\b{abbr}\b', hindi_pronunciation, text)
            
        return text

abbreviation_normalizer = AbbreviationNormalizer()
