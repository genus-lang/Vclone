import re

class NumberNormalizer:
    def __init__(self):
        self.hindi_digits = {
            '0': 'शून्य', '1': 'एक', '2': 'दो', '3': 'तीन', '4': 'चार',
            '5': 'पांच', '6': 'छह', '7': 'सात', '8': 'आठ', '9': 'नौ'
        }
        
        self.hindi_tens = {
            '10': 'दस', '11': 'ग्यारह', '12': 'बारह', '13': 'तेरह', '14': 'चौदह',
            '15': 'पंद्रह', '16': 'सोलह', '17': 'सत्रह', '18': 'अठारह', '19': 'उन्नीस',
            '20': 'बीस', '30': 'तीस', '40': 'चालीस', '50': 'पचास', '60': 'साठ',
            '70': 'सत्तर', '80': 'अस्सी', '90': 'नब्बे', '100': 'सौ'
        }
        
        # A full num2words for Hindi can be complex, but for basic webnovels we handle 
        # digit-by-digit for long IDs and basic translation for small numbers.
        
    def normalize(self, text: str, lang: str = "hi") -> str:
        if lang != "hi":
            return text
            
        # Pattern for numbers like 3-2048 or 98%
        # First, handle simple English number words sometimes found in Hinglish
        text = text.replace("million", "मिलियन").replace("billion", "बिलियन")
        text = text.replace("%", " प्रतिशत")
        
        # Replace standalone simple numbers up to 20
        for num, word in sorted(self.hindi_tens.items(), key=lambda x: int(x[0]), reverse=True):
            text = re.sub(rf'\b{num}\b', word, text)
            
        # Fallback: replace any remaining individual digits
        for digit, word in self.hindi_digits.items():
            text = text.replace(digit, f" {word} ")
            
        # Clean up double spaces created by digit replacement
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

number_normalizer = NumberNormalizer()
