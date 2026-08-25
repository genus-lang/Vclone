import os
import sys
import json
from datetime import datetime

# Setup paths so we can import from backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from backend.database import engine, Base, SessionLocal
from backend.models import Voice, VoiceSettings, GeneratedAudio

def migrate():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Migrate Voices
    voices_file = os.path.join(BASE_DIR, "voices.json")
    if os.path.exists(voices_file):
        with open(voices_file, "r", encoding="utf-8") as f:
            try:
                voices_data = json.load(f)
                print(f"Found {len(voices_data)} voices in voices.json")
                
                for v_id, meta in voices_data.items():
                    # Check if already exists
                    existing = db.query(Voice).filter(Voice.id == v_id).first()
                    if not existing:
                        engine_name = meta.get("engine", "unknown")
                        # Handle old data missing language or engine voice id
                        lang = meta.get("languages", ["hi-IN"])[0] if meta.get("languages") else "hi-IN"
                        
                        is_cloned = (engine_name == "xtts" and "output/" in meta.get("preview", ""))
                        
                        new_voice = Voice(
                            id=v_id,
                            name=meta.get("name", v_id),
                            engine=engine_name,
                            engine_voice_id=v_id, # Can be updated later
                            language=lang,
                            is_cloned=is_cloned
                        )
                        db.add(new_voice)
                        
                        # Add default settings
                        settings = VoiceSettings(
                            voice_id=v_id,
                            speed=1.0,
                            stability=0.5,
                            similarity=0.75,
                            style=0.0,
                            pitch=0.0,
                            volume=1.0
                        )
                        db.add(settings)
                        
                db.commit()
                print("Voices migrated successfully.")
            except Exception as e:
                print(f"Error migrating voices: {e}")
                
    # Migrate History
    history_file = os.path.join(BASE_DIR, "output", "history.json")
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            try:
                history_data = json.load(f)
                print(f"Found {len(history_data)} history items in history.json")
                
                for item in history_data:
                    existing = db.query(GeneratedAudio).filter(GeneratedAudio.id == item["id"]).first()
                    if not existing:
                        # create timestamp
                        created = datetime.fromtimestamp(item.get("created_at", datetime.utcnow().timestamp()))
                        
                        audio = GeneratedAudio(
                            id=item["id"],
                            voice_id=item.get("voice"),
                            text_hash=item.get("text", "")[:50], # Just a rough hash/preview for now
                            audio_path=item.get("audio_url", "").replace("/v1/audio/", "output/audio/"),
                            created_at=created
                        )
                        db.add(audio)
                        
                db.commit()
                print("History migrated successfully.")
            except Exception as e:
                print(f"Error migrating history: {e}")

    db.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
