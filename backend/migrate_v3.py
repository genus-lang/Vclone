import os
import sys

# Ensure backend modules can be imported
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from backend.database import engine, Base
from backend.models import PronunciationDictionary, VoiceProfile, VoiceReference

def migrate():
    print("Creating new tables for V3 (Pronunciation, Profiles, References)...")
    Base.metadata.create_all(bind=engine)
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
