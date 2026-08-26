"""
G2P / Hinglish Normalizer
=========================
Token-level classifier + normalizer for Hindi/English/Hinglish text.

Pipeline per token:
  1. Check user pronunciation dictionary (highest priority)
  2. Check known abbreviations (VR → वी आर)
  3. Check known entities (Fu Qian → फू चिएन)
  4. Classify: pure Hindi | pure English | number | Hinglish function word
  5. Apply appropriate normalization

This is the highest-priority quality module because correct text going
into XTTS directly fixes pronunciation issues that no amount of audio
post-processing can repair.

IMPORTANT: We do NOT transliterate every English word — only those that
are in a Hindi context and would be mis-pronounced by XTTS without help.
"""
import re
from typing import Dict, List, Tuple

# ---- Phoneme mapping tables ----

# English consonant clusters → Hindi approximations (rule-based)
CONSONANT_MAP = {
    "ch": "च", "sh": "श", "th": "थ", "ph": "फ",
    "gh": "ग", "kh": "ख", "wh": "व",
    "tr": "ट्र", "pr": "प्र", "br": "ब्र", "gr": "ग्र",
    "str": "स्ट्र", "spr": "स्प्र",
    "qu": "क्व",
}

VOWEL_MAP = {
    "a": "अ", "aa": "आ", "i": "इ", "ee": "ई", "ii": "ई",
    "u": "उ", "oo": "ऊ", "uu": "ऊ", "e": "ए", "ai": "ऐ",
    "o": "ओ", "au": "औ", "ow": "ओ", "aw": "ऑ",
    "ea": "ई", "ie": "आई", "oa": "ओ",
}

# Common English letters standalone pronunciation in Hindi context
SINGLE_LETTER_HI = {
    "a": "ए", "b": "बी", "c": "सी", "d": "डी", "e": "ई",
    "f": "एफ", "g": "जी", "h": "एच", "i": "आई", "j": "जे",
    "k": "के", "l": "एल", "m": "एम", "n": "एन", "o": "ओ",
    "p": "पी", "q": "क्यू", "r": "आर", "s": "एस", "t": "टी",
    "u": "यू", "v": "वी", "w": "डब्ल्यू", "x": "एक्स",
    "y": "वाई", "z": "ज़ेड",
}

# Known abbreviations (uppercase → Hindi pronunciation)
ABBREVIATIONS: Dict[str, str] = {
    "VR": "वी आर",
    "AR": "ए आर",
    "AI": "ए आई",
    "ML": "एम एल",
    "TTS": "टी टी एस",
    "ID": "आई डी",
    "OTP": "ओ टी पी",
    "ATM": "ए टी एम",
    "DNA": "डी एन ए",
    "CPU": "सी पी यू",
    "GPU": "जी पी यू",
    "RAM": "रैम",
    "ROM": "रोम",
    "SIM": "सिम",
    "PDF": "पी डी एफ",
    "OK": "ओके",
    "PM": "पी एम",
    "CM": "सी एम",
    "SMS": "एस एम एस",
    "TV": "टी वी",
    "AC": "ए सी",
    "DC": "डी सी",
    "FC": "एफ सी",
    "SAN": "सैन",
    "HP": "एच पी",
    "EV": "ई वी",
    "EMI": "ई एम आई",
}

# Hinglish function words that should be kept as-is (already XTTS handles well)
HINGLISH_PASSTHROUGH = {
    "mein", "ka", "ki", "ke", "hai", "hain", "tha", "thi", "the",
    "kya", "toh", "par", "aur", "ya", "nahi", "hoga", "hua", "hui",
    "bhi", "sirf", "lekin", "kyunki", "isliye", "agar", "tab",
}

# English words that commonly appear in Hinglish and should be transliterated
COMMON_EN_IN_HI: Dict[str, str] = {
    "device": "डिवाइस",
    "mobile": "मोबाइल",
    "phone": "फोन",
    "computer": "कंप्यूटर",
    "internet": "इंटरनेट",
    "network": "नेटवर्क",
    "password": "पासवर्ड",
    "button": "बटन",
    "screen": "स्क्रीन",
    "camera": "कैमरा",
    "battery": "बैटरी",
    "cable": "केबल",
    "signal": "सिग्नल",
    "app": "ऐप",
    "update": "अपडेट",
    "download": "डाउनलोड",
    "upload": "अपलोड",
    "video": "वीडियो",
    "audio": "ऑडियो",
    "data": "डेटा",
    "server": "सर्वर",
    "file": "फाइल",
    "folder": "फोल्डर",
    "game": "गेम",
    "online": "ऑनलाइन",
    "offline": "ऑफलाइन",
    "website": "वेबसाइट",
    "email": "ईमेल",
    "call": "कॉल",
    "chat": "चैट",
    "message": "मैसेज",
    "software": "सॉफ्टवेयर",
    "hardware": "हार्डवेयर",
    "point": "पॉइंट",
    "points": "पॉइंट्स",
    "level": "लेवल",
    "score": "स्कोर",
    "team": "टीम",
    "player": "प्लेयर",
    "match": "मैच",
    "train": "ट्रेन",
    "station": "स्टेशन",
    "hospital": "हॉस्पिटल",
    "market": "मार्केट",
    "bank": "बैंक",
    "card": "कार्ड",
    "cash": "कैश",
    "ticket": "टिकट",
    "police": "पुलिस",
    "doctor": "डॉक्टर",
    "manager": "मैनेजर",
    "officer": "ऑफिसर",
    "college": "कॉलेज",
    "school": "स्कूल",
    "class": "क्लास",
    "test": "टेस्ट",
    "result": "रिज़ल्ट",
    "report": "रिपोर्ट",
    "project": "प्रोजेक्ट",
}

HINDI_CHARS = re.compile(r'[\u0900-\u097F]')
ENGLISH_WORD = re.compile(r'^[a-zA-Z]+$')
NUMBER = re.compile(r'^\d+(\.\d+)?$')
ABBREV = re.compile(r'^[A-Z]{2,5}$')


class HinglishG2P:
    def __init__(self, custom_dict: Dict[str, str] = None):
        self.custom_dict = custom_dict or {}

    def set_custom_dict(self, d: Dict[str, str]):
        self.custom_dict = d

    def _is_hindi(self, word: str) -> bool:
        return bool(HINDI_CHARS.search(word))

    def _classify_token(self, word: str) -> str:
        clean = re.sub(r"[^\w]", "", word)
        if not clean:
            return "punctuation"
        if self._is_hindi(clean):
            return "hindi"
        if ABBREV.match(clean):
            return "abbrev"
        if NUMBER.match(clean):
            return "number"
        if ENGLISH_WORD.match(clean):
            return "english"
        return "mixed"

    def normalize_token(self, word: str, context_is_hindi: bool = False) -> Tuple[str, str]:
        """
        Returns (normalized_word, token_type).
        normalized_word: the TTS-ready version.
        token_type: 'hindi' | 'english' | 'abbrev' | 'number' | 'transliterated'
        """
        punctuation_suffix = ""
        # Extract trailing punctuation
        match = re.match(r'^(.*?)([,\.\?\!\:;।…]+)$', word)
        if match:
            word = match.group(1)
            punctuation_suffix = match.group(2)

        if not word:
            return punctuation_suffix, "punctuation"

        clean_lower = word.lower()

        # 1. Custom pronunciation dictionary (highest priority)
        if clean_lower in self.custom_dict:
            return self.custom_dict[clean_lower] + punctuation_suffix, "custom"
        if word in self.custom_dict:
            return self.custom_dict[word] + punctuation_suffix, "custom"

        # 2. Hindi — pass through
        if self._is_hindi(word):
            return word + punctuation_suffix, "hindi"

        # 3. Known abbreviation
        if ABBREV.match(word) and word.upper() in ABBREVIATIONS:
            return ABBREVIATIONS[word.upper()] + punctuation_suffix, "abbrev"

        # 4. Hinglish passthrough (common words XTTS handles natively)
        if clean_lower in HINGLISH_PASSTHROUGH:
            return word + punctuation_suffix, "hinglish"

        # 5. Common English-in-Hindi words
        if context_is_hindi and clean_lower in COMMON_EN_IN_HI:
            return COMMON_EN_IN_HI[clean_lower] + punctuation_suffix, "transliterated"

        # 6. Number
        if NUMBER.match(word):
            return word + punctuation_suffix, "number"  # Handled separately by numbers.py

        # 7. Pure English in English context — pass through
        return word + punctuation_suffix, "english"

    def normalize_sentence(self, text: str, context_lang: str = "hi") -> str:
        """
        Normalize a full sentence token by token.
        context_lang: 'hi' triggers transliteration of English words in Hindi context.
        """
        context_is_hindi = (context_lang == "hi")
        tokens = text.split()
        result = []
        for token in tokens:
            normalized, _ = self.normalize_token(token, context_is_hindi)
            result.append(normalized)
        return " ".join(result)


g2p_processor = HinglishG2P()
