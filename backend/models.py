from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class Voice(Base):
    __tablename__ = "voices"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    engine = Column(String, nullable=False)
    engine_voice_id = Column(String)
    language = Column(String)
    is_cloned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    settings = relationship("VoiceSettings", back_populates="voice", uselist=False, cascade="all, delete-orphan")
    versions = relationship("VoiceVersion", back_populates="voice", cascade="all, delete-orphan")


class VoiceSettings(Base):
    __tablename__ = "voice_settings"

    voice_id = Column(String, ForeignKey("voices.id"), primary_key=True)
    
    # Native & Shared
    speed = Column(Float, default=1.0)
    pitch = Column(Float, default=0.0)
    stability = Column(Float, default=0.5)
    similarity = Column(Float, default=0.75)
    expressiveness = Column(Float, default=0.5)
    
    # Audio DSP
    energy = Column(Float, default=0.5)
    warmth = Column(Float, default=0.5)
    breathiness = Column(Float, default=0.1)
    clarity = Column(Float, default=0.8)
    resonance = Column(Float, default=0.5)
    
    # Text/Prosody
    pause_length = Column(Float, default=0.5)
    sentence_variation = Column(Float, default=0.5)
    emphasis = Column(Float, default=0.5)
    emotion = Column(String, default="neutral")
    
    preset = Column(String, default="natural")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    voice = relationship("Voice", back_populates="settings")


class VoiceVersion(Base):
    __tablename__ = "voice_versions"

    id = Column(String, primary_key=True)
    voice_id = Column(String, ForeignKey("voices.id"))
    name = Column(String, nullable=False)
    settings_json = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    voice = relationship("Voice", back_populates="versions")


class GeneratedAudio(Base):
    __tablename__ = "generated_audio"

    id = Column(String, primary_key=True)
    voice_id = Column(String, ForeignKey("voices.id"))
    version_id = Column(String, ForeignKey("voice_versions.id"), nullable=True)
    text_hash = Column(String)
    settings_hash = Column(String)
    engine = Column(String)
    model = Column(String)
    audio_path = Column(String)
    format = Column(String)
    duration = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class PronunciationDictionary(Base):
    __tablename__ = "pronunciation_dictionary"
    
    id = Column(String, primary_key=True)
    original_word = Column(String, nullable=False)
    replacement_word = Column(String, nullable=False)
    language = Column(String, default="all")
    created_at = Column(DateTime, default=datetime.utcnow)

class VoiceProfile(Base):
    __tablename__ = "voice_profiles"
    
    id = Column(String, primary_key=True)
    voice_id = Column(String, ForeignKey("voices.id"))
    name = Column(String, nullable=False) # e.g. "Natural", "Dramatic"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    references = relationship("VoiceReference", back_populates="profile", cascade="all, delete-orphan")
    voice = relationship("Voice")

class VoiceReference(Base):
    __tablename__ = "voice_references"
    
    id = Column(String, primary_key=True)
    profile_id = Column(String, ForeignKey("voice_profiles.id"))
    file_path = Column(String, nullable=False)
    transcript = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Quality metrics (populated by ReferenceManager.score_reference)
    quality_score = Column(Integer, nullable=True)       # 0-100
    snr_db = Column(Float, nullable=True)                # Signal-to-noise ratio dB
    speech_density = Column(Float, nullable=True)        # 0.0-1.0 (% of audio with speech)
    silence_ratio = Column(Float, nullable=True)         # 0.0-1.0
    peak_db = Column(Float, nullable=True)               # dBFS
    dynamic_range_db = Column(Float, nullable=True)
    has_clipping = Column(Boolean, nullable=True)
    
    profile = relationship("VoiceProfile", back_populates="references")

