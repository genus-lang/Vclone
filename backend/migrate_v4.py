"""migrate_v4.py — Add quality metric columns to voice_references"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tts_platform.db")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

cols_to_add = [
    ("quality_score",    "INTEGER"),
    ("snr_db",           "REAL"),
    ("speech_density",   "REAL"),
    ("silence_ratio",    "REAL"),
    ("peak_db",          "REAL"),
    ("dynamic_range_db", "REAL"),
    ("has_clipping",     "INTEGER"),
]

existing = [row[1] for row in c.execute("PRAGMA table_info(voice_references)").fetchall()]

for col, coltype in cols_to_add:
    if col not in existing:
        c.execute(f"ALTER TABLE voice_references ADD COLUMN {col} {coltype}")
        print(f"Added column: {col}")
    else:
        print(f"Column already exists: {col}")

conn.commit()
conn.close()
print("Migration v4 complete.")
