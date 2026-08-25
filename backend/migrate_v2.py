import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "tts_platform.db")

def migrate():
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Add new columns to voice_settings
    columns_to_add = [
        ("expressiveness", "FLOAT", "0.5"),
        ("energy", "FLOAT", "0.5"),
        ("warmth", "FLOAT", "0.5"),
        ("breathiness", "FLOAT", "0.1"),
        ("clarity", "FLOAT", "0.8"),
        ("resonance", "FLOAT", "0.5"),
        ("pause_length", "FLOAT", "0.5"),
        ("sentence_variation", "FLOAT", "0.5"),
        ("emphasis", "FLOAT", "0.5")
    ]
    
    for col_name, col_type, default_val in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE voice_settings ADD COLUMN {col_name} {col_type} DEFAULT {default_val}")
            print(f"Added column {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {e}")
                
    # 2. Add version_id to generated_audio
    try:
        cursor.execute(f"ALTER TABLE generated_audio ADD COLUMN version_id VARCHAR")
        print("Added column version_id to generated_audio")
    except sqlite3.OperationalError as e:
        pass

    # 3. Create voice_versions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voice_versions (
        id VARCHAR PRIMARY KEY,
        voice_id VARCHAR REFERENCES voices(id),
        name VARCHAR NOT NULL,
        settings_json VARCHAR NOT NULL,
        created_at DATETIME,
        updated_at DATETIME
    )
    """)
    print("Created voice_versions table")
    
    # 4. Drop voice_presets if it exists
    cursor.execute("DROP TABLE IF EXISTS voice_presets")
    print("Dropped old voice_presets table")

    conn.commit()
    conn.close()
    print("Migration V2 complete!")

if __name__ == "__main__":
    migrate()
