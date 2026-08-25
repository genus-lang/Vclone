import re
import os
import sys

# Ensure backend modules can be imported
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from backend.database import SessionLocal
from backend.models import PronunciationDictionary as PronunciationModel

class PronunciationDictionary:
    def apply(self, text: str) -> str:
        db = SessionLocal()
        try:
            items = db.query(PronunciationModel).all()
            processed_text = text
            # Sort keys by length descending to prevent partial match issues (e.g. replacing 'Fu' before 'Fu Qian')
            sorted_items = sorted(items, key=lambda x: len(x.original_word), reverse=True)
            
            for item in sorted_items:
                # Use regex for word boundaries if the word is purely alphanumeric, 
                # otherwise standard replace
                if re.match(r'^[\w\s]+$', item.original_word):
                    pattern = re.compile(rf'\b{re.escape(item.original_word)}\b', re.IGNORECASE)
                    processed_text = pattern.sub(item.replacement_word, processed_text)
                else:
                    processed_text = processed_text.replace(item.original_word, item.replacement_word)
                
            return processed_text
        finally:
            db.close()

pronunciation_dict = PronunciationDictionary()
