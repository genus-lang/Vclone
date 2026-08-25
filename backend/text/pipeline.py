from backend.text.normalizer import text_normalizer
from backend.text.abbreviations import abbreviation_normalizer
from backend.text.numbers import number_normalizer
from backend.text.pronunciation import pronunciation_dict
from backend.text.language_detector import language_detector
import re

# We use a robust regex to split by sentence endings, accounting for quotes and newlines
def split_into_sentences(text: str):
    # Split by standard sentence terminators, keeping the terminator
    sentences = re.split(r'([.!?।]+[\'"]?\s*)', text)
    
    # Reconstruct sentences from the split (text, terminator, text, terminator...)
    result = []
    current = ""
    for i in range(0, len(sentences)-1, 2):
        chunk = (sentences[i] + sentences[i+1]).strip()
        if chunk:
            result.append(chunk)
    
    if len(sentences) % 2 != 0 and sentences[-1].strip():
        result.append(sentences[-1].strip())
        
    return result

class TextPipeline:
    def process_chapter(self, text: str, target_lang: str = "hi"):
        """Process an entire chapter and return a list of text chunks ready for TTS."""
        
        # 1. Base Normalization
        text = text_normalizer.normalize(text, target_lang)
        
        # 2. Pronunciation Dictionary (User overrides take precedence)
        text = pronunciation_dict.apply(text)
        
        # 3. Abbreviations
        text = abbreviation_normalizer.normalize(text, target_lang)
        
        # 4. Numbers
        text = number_normalizer.normalize(text, target_lang)
        
        # 5. Sentence Segmentation
        sentences = split_into_sentences(text)
        
        # 6. Hard constraint chunking
        final_chunks = []
        for sentence in sentences:
            if len(sentence) > 150:
                # If still too long, chunk aggressively by commas or just words
                parts = sentence.split(',')
                for p in parts:
                    p = p.strip()
                    if not p: continue
                    if len(p) > 150:
                        # Hard split by words up to limit
                        words = p.split()
                        current_chunk = []
                        current_len = 0
                        for w in words:
                            if current_len + len(w) > 140:
                                final_chunks.append(" ".join(current_chunk))
                                current_chunk = [w]
                                current_len = len(w)
                            else:
                                current_chunk.append(w)
                                current_len += len(w) + 1
                        if current_chunk:
                            final_chunks.append(" ".join(current_chunk))
                    else:
                        final_chunks.append(p)
            else:
                final_chunks.append(sentence)
                
        return final_chunks

text_pipeline = TextPipeline()
