import re

class ProsodyProcessor:
    def segment(self, text: str) -> list[str]:
        """
        Intelligently chunks text into 1-5 sentence blocks depending on length.
        Avoids splitting every single period, which breaks natural flow.
        """
        # Split roughly by sentence-ending punctuation, keeping the punctuation
        # This handles English (.), Hindi (।), Exclamation (!), Question (?)
        raw_sentences = re.split(r'(?<=[.!?।])\s+', text.strip())
        
        chunks = []
        current_chunk = ""
        
        for sentence in raw_sentences:
            if not sentence.strip():
                continue
                
            # If current chunk is getting long (e.g. > 200 chars), push it and start new
            if len(current_chunk) + len(sentence) > 250 and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

prosody_processor = ProsodyProcessor()
