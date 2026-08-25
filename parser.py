import re

def normalize_text(text: str) -> str:
    """
    Cleans up text before passing it to TTS models.
    Removes strange symbols, normalizes punctuation, and ensures proper spacing.
    """
    # Replace multiple question marks/exclamation points with a single one
    text = re.sub(r'\?+', '?', text)
    text = re.sub(r'!+', '!', text)
    
    # Remove emojis or very weird characters if necessary (keeping Hindi/English and basic punctuation)
    # This regex keeps alphanumeric, spaces, and standard punctuation.
    # We include Devangari Unicode range \u0900-\u097F
    text = re.sub(r'[^\w\s\.,!\?\'"-\u0900-\u097F]', '', text)
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def parse_chapter(text: str):
    """
    Parses a chapter into a list of dictionaries with text and speaker.
    Lines starting with [speaker_name] are assigned to that speaker.
    Otherwise, they default to narrator.
    """
    lines = text.strip().split('\n')
    chunks = []
    
    tag_pattern = re.compile(r'^\[([a-zA-Z0-9_-]+)\]\s*(.*)')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        match = tag_pattern.match(line)
        if match:
            speaker = match.group(1).lower()
            spoken_text = match.group(2).strip()
            if spoken_text:
                normalized = normalize_text(spoken_text)
                if normalized:
                    chunks.append({"speaker": speaker, "text": normalized})
        else:
            normalized = normalize_text(line)
            if normalized:
                chunks.append({"speaker": "narrator", "text": normalized})
            
    return chunks
