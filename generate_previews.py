import os
from engines import engine_manager

def main():
    os.makedirs("frontend/audio/previews", exist_ok=True)
    
    test_phrase_hi = "आज रात शहर बिल्कुल शांत था, लेकिन आरव जानता था कि कुछ बहुत बड़ा होने वाला है।"
    test_phrase_en = "The city was completely silent tonight, but Aarav knew something was about to happen."
    
    for voice_id, meta in engine_manager.voice_registry.items():
        output_path = f"frontend/audio/previews/{voice_id}.mp3"
        
        # Languages now look like ["hi-IN", "en-IN"]
        is_hindi = any("hi" in lang for lang in meta["languages"])
        text = test_phrase_hi if is_hindi else test_phrase_en
        language = "hi" if is_hindi else "en"
        
        print(f"Generating preview for {voice_id} ({meta['name']})...")
        try:
            engine_manager.generate(
                text=text,
                voice_id=voice_id,
                language=language,
                output_path=output_path
            )
            print(f"SUCCESS: Generated {output_path}")
        except Exception as e:
            print(f"ERROR: Failed for {voice_id}: {e}")

if __name__ == "__main__":
    main()
