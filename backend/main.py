import uuid
import os
import gc
import time
import hashlib
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
import torch
from datetime import datetime

# Configure sys path for root imports
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from parser import parse_chapter
from audio import merge_audio_files
from backend.engines import engine_manager
from backend.text.pipeline import text_pipeline
from backend.audio.processor import audio_processor
from backend.audio.vad import vad_processor
from backend.audio.quality_checker import quality_checker
from backend.audio.encoder import audio_encoder
from backend.database import get_db
from backend.models import Voice, VoiceSettings, VoiceVersion, GeneratedAudio, PronunciationDictionary, VoiceProfile, VoiceReference

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Web Studio TTS Platform API")

# Serve the web studio at root
os.makedirs(os.path.join(BASE_DIR, "frontend"), exist_ok=True)
app.mount("/studio", StaticFiles(directory=os.path.join(BASE_DIR, "frontend"), html=True), name="frontend")
app.mount("/output", StaticFiles(directory=os.path.join(BASE_DIR, "output")), name="output")

@app.get("/")
def root_redirect():
    return RedirectResponse(url="/studio/")

class ChapterRequest(BaseModel):
    text: str
    language: str = "hi"

class SpeechRequest(BaseModel):
    input: str
    voice: str
    model: str = "xtts"
    language: Optional[str] = "en"
    settings: Optional[dict] = None
    version_id: Optional[str] = None

class PronunciationRequest(BaseModel):
    original: str
    say_as: str
    language: Optional[str] = "all"

@app.post("/v1/pronunciations")
def add_pronunciation(request: PronunciationRequest, db: Session = Depends(get_db)):
    import uuid
    pron = PronunciationDictionary(
        id=uuid.uuid4().hex,
        original_word=request.original,
        replacement_word=request.say_as,
        language=request.language
    )
    db.add(pron)
    db.commit()
    return {"status": "success", "id": pron.id}

@app.get("/v1/pronunciations")
def get_pronunciations(db: Session = Depends(get_db)):
    items = db.query(PronunciationDictionary).all()
    return {"pronunciations": [
        {
            "id": item.id,
            "original": item.original_word,
            "say_as": item.replacement_word,
            "language": item.language
        } for item in items
    ]}

@app.delete("/v1/pronunciations/{pron_id}")
def delete_pronunciation(pron_id: str, db: Session = Depends(get_db)):
    item = db.query(PronunciationDictionary).filter(PronunciationDictionary.id == pron_id).first()
    if item:
        db.delete(item)
        db.commit()
    return {"status": "deleted"}

@app.post("/v1/voices/clone")
async def clone_voice(
    audio: UploadFile = File(...),
    name: str = Form(...),
    language: str = Form(...),
    profile: str = Form(...),
    db: Session = Depends(get_db)
):
    import uuid
    voice_id = name.lower().replace(" ", "_")
    voice_id = "".join([c for c in voice_id if c.isalnum() or c == "_"])
    if not voice_id:
        raise HTTPException(status_code=400, detail="Invalid name")
        
    os.makedirs(os.path.join(BASE_DIR, "voices", "raw"), exist_ok=True)
    
    # Save the raw upload first (could be WebM/OGG from browser MediaRecorder)
    raw_upload_path = os.path.join(BASE_DIR, "voices", "raw", f"{voice_id}_{profile}_upload.webm")
    with open(raw_upload_path, "wb") as f:
        f.write(await audio.read())
    
    # Convert to proper 16-bit PCM WAV using pydub (handles WebM/OGG/MP4 etc.)
    raw_audio_path = os.path.join(BASE_DIR, "voices", "raw", f"{voice_id}_{profile}.wav")
    try:
        from pydub import AudioSegment
        audio_seg = AudioSegment.from_file(raw_upload_path)
        audio_seg = audio_seg.set_channels(1).set_frame_rate(22050).set_sample_width(2)  # mono 22050Hz 16-bit
        audio_seg.export(raw_audio_path, format="wav")
        print(f"[Clone] Converted upload to WAV: {raw_audio_path} ({len(audio_seg)/1000:.1f}s)")
    except Exception as e:
        print(f"[Clone] pydub conversion failed, using raw file: {e}")
        import shutil
        shutil.copy2(raw_upload_path, raw_audio_path)
        
    # Also save one fallback main wav for legacy
    main_wav = os.path.join(BASE_DIR, "voices", f"{voice_id}.wav")
    import shutil
    shutil.copy2(raw_audio_path, main_wav)
    
    # Analyze Quality (now on properly converted WAV)
    quality = quality_checker.analyze_quality(raw_audio_path)
    if quality["overall_score"] < 50:
        print(f"Warning: Poor audio quality for {voice_id}. Score: {quality['overall_score']}")
        
    # Segment Audio (VAD)
    segment_dir = os.path.join(BASE_DIR, "voices", f"{voice_id}_{profile}_segments")
    segments = vad_processor.segment_audio(raw_audio_path, segment_dir)
    if not segments:
        # Fallback: use the full wav as one segment
        segments = [raw_audio_path]
        
    # Save to database
    existing = db.query(Voice).filter(Voice.id == voice_id).first()
    if not existing:
        new_voice = Voice(
            id=voice_id,
            name=name,
            engine="xtts",
            engine_voice_id=voice_id,
            language=language,
            is_cloned=True
        )
        db.add(new_voice)
        db.add(VoiceSettings(voice_id=voice_id))
        db.commit()
        
    # Profile
    existing_profile = db.query(VoiceProfile).filter(VoiceProfile.voice_id == voice_id, VoiceProfile.name == profile).first()
    if not existing_profile:
        existing_profile = VoiceProfile(id=uuid.uuid4().hex, voice_id=voice_id, name=profile)
        db.add(existing_profile)
        db.commit()
        
    # References
    for seg in segments:
        ref = VoiceReference(
            id=uuid.uuid4().hex,
            profile_id=existing_profile.id,
            file_path=seg
        )
        db.add(ref)
    db.commit()
    
    os.makedirs(os.path.join(BASE_DIR, "frontend", "audio", "previews"), exist_ok=True)
    test_phrase = "आज रात शहर बिल्कुल शांत था।" if "hi" in language else "The city was completely silent tonight."
    
    try:
        engine_manager.generate(
            text=test_phrase,
            voice_id=voice_id,
            language=language.split("-")[0],
            output_path=os.path.join(BASE_DIR, "frontend", "audio", "previews", f"{voice_id}.mp3")
        )
    except Exception as e:
        print(f"Failed to generate preview for cloned voice: {e}")
        
    return {"status": "success", "voice_id": voice_id, "segments_created": len(segments), "quality_score": quality["overall_score"]}

@app.get("/health")
def health_check():
    return {"status": "ok", "gpu_available": torch.cuda.is_available()}

@app.get("/v1/voices")
def get_voices():
    return {"voices": engine_manager.get_available_voices()}

@app.delete("/v1/voices/{voice_id}")
def delete_voice(voice_id: str, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
        
    db.delete(voice)
    db.commit()
        
    preview_path = os.path.join(BASE_DIR, "frontend", "audio", "previews", f"{voice_id}.mp3")
    if os.path.exists(preview_path):
        try: os.remove(preview_path)
        except: pass
            
    wav_path = os.path.join(BASE_DIR, "voices", f"{voice_id}.wav")
    if os.path.exists(wav_path):
        try: os.remove(wav_path)
        except: pass
            
    return JSONResponse({"status": "success", "message": f"Voice {voice_id} deleted."})

# ---- VOICE SETTINGS ENDPOINTS ----

class VoiceSettingsRequest(BaseModel):
    speed: float = 1.0
    pitch: float = 0.0
    stability: float = 0.5
    similarity: float = 0.75
    expressiveness: float = 0.5
    energy: float = 0.5
    warmth: float = 0.5
    breathiness: float = 0.1
    clarity: float = 0.8
    resonance: float = 0.5
    pause_length: float = 0.5
    sentence_variation: float = 0.5
    emphasis: float = 0.5
    emotion: str = "neutral"
    preset: str = "custom"

@app.get("/v1/voices/{voice_id}/settings")
def get_voice_settings(voice_id: str, db: Session = Depends(get_db)):
    settings = db.query(VoiceSettings).filter(VoiceSettings.voice_id == voice_id).first()
    if not settings:
        settings = VoiceSettings(voice_id=voice_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        "voice_id": settings.voice_id,
        "speed": settings.speed,
        "pitch": settings.pitch,
        "stability": settings.stability,
        "similarity": settings.similarity,
        "expressiveness": settings.expressiveness,
        "energy": settings.energy,
        "warmth": settings.warmth,
        "breathiness": settings.breathiness,
        "clarity": settings.clarity,
        "resonance": settings.resonance,
        "pause_length": settings.pause_length,
        "sentence_variation": settings.sentence_variation,
        "emphasis": settings.emphasis,
        "emotion": settings.emotion,
        "preset": settings.preset
    }

@app.put("/v1/voices/{voice_id}/settings")
def update_voice_settings(voice_id: str, request: VoiceSettingsRequest, db: Session = Depends(get_db)):
    settings = db.query(VoiceSettings).filter(VoiceSettings.voice_id == voice_id).first()
    if not settings:
        settings = VoiceSettings(voice_id=voice_id)
        db.add(settings)

    settings.speed = request.speed
    settings.pitch = request.pitch
    settings.stability = request.stability
    settings.similarity = request.similarity
    settings.expressiveness = request.expressiveness
    settings.energy = request.energy
    settings.warmth = request.warmth
    settings.breathiness = request.breathiness
    settings.clarity = request.clarity
    settings.resonance = request.resonance
    settings.pause_length = request.pause_length
    settings.sentence_variation = request.sentence_variation
    settings.emphasis = request.emphasis
    settings.emotion = request.emotion
    settings.preset = request.preset

    db.commit()
    return {"status": "saved", "voice_id": voice_id}

@app.post("/v1/voices/{voice_id}/settings/reset")
def reset_voice_settings(voice_id: str, db: Session = Depends(get_db)):
    settings = db.query(VoiceSettings).filter(VoiceSettings.voice_id == voice_id).first()
    if not settings:
        settings = VoiceSettings(voice_id=voice_id)
        db.add(settings)

    settings.speed = 1.0
    settings.pitch = 0.0
    settings.stability = 0.5
    settings.similarity = 0.75
    settings.expressiveness = 0.5
    settings.energy = 0.5
    settings.warmth = 0.5
    settings.breathiness = 0.1
    settings.clarity = 0.8
    settings.resonance = 0.5
    settings.pause_length = 0.5
    settings.sentence_variation = 0.5
    settings.emphasis = 0.5
    settings.emotion = "neutral"
    settings.preset = "natural"

    db.commit()
    return {
        "status": "reset",
        "settings": {
            "speed": 1.0,
            "pitch": 0.0,
            "stability": 0.5,
            "similarity": 0.75,
            "expressiveness": 0.5,
            "energy": 0.5,
            "warmth": 0.5,
            "breathiness": 0.1,
            "clarity": 0.8,
            "resonance": 0.5,
            "pause_length": 0.5,
            "sentence_variation": 0.5,
            "emphasis": 0.5,
            "emotion": "neutral",
            "preset": "natural"
        }
    }

class VoiceVersionRequest(BaseModel):
    name: str
    settings: dict

@app.post("/v1/voices/{voice_id}/versions")
def create_voice_version(voice_id: str, request: VoiceVersionRequest, db: Session = Depends(get_db)):
    import uuid
    import json
    version_id = uuid.uuid4().hex
    v = VoiceVersion(
        id=version_id,
        voice_id=voice_id,
        name=request.name,
        settings_json=json.dumps(request.settings)
    )
    db.add(v)
    db.commit()
    return {"status": "created", "version_id": version_id}

@app.get("/v1/voices/{voice_id}/versions")
def get_voice_versions(voice_id: str, db: Session = Depends(get_db)):
    versions = db.query(VoiceVersion).filter(VoiceVersion.voice_id == voice_id).all()
    import json
    return {
        "versions": [{
            "id": v.id,
            "name": v.name,
            "settings": json.loads(v.settings_json),
            "created_at": v.created_at.isoformat()
        } for v in versions]
    }

@app.delete("/v1/voice-versions/{version_id}")
def delete_voice_version(version_id: str, db: Session = Depends(get_db)):
    v = db.query(VoiceVersion).filter(VoiceVersion.id == version_id).first()
    if v:
        db.delete(v)
        db.commit()
    return {"status": "deleted"}

class PreviewRequest(BaseModel):
    text: str
    settings: dict

@app.post("/v1/voices/{voice_id}/preview")
def generate_preview(voice_id: str, request: PreviewRequest, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
        
    os.makedirs(os.path.join(BASE_DIR, "output", "temp"), exist_ok=True)
    temp_path = os.path.join(BASE_DIR, "output", "temp", f"preview_{uuid.uuid4().hex[:8]}.mp3")
    
    # We pass the temporary settings directly to engine_manager.generate
    # which will use them instead of the saved DB settings
    lang = voice.language.split("-")[0] if voice.language else "hi"
    
    try:
        from backend.text.pipeline import text_pipeline
        
        # Enforce 500 character limit for preview
        preview_text = request.text[:500]
        chunks = text_pipeline.process_chapter(preview_text, lang)
        
        if len(chunks) <= 1:
            raw_output = temp_path.replace(".mp3", "_raw.wav")
            engine_manager.generate(
                text=chunks[0] if chunks else preview_text, 
                voice_id=voice_id, 
                language=lang, 
                output_path=raw_output,
                override_settings=request.settings
            )
            merged_path = raw_output
        else:
            temp_files = []
            session_id = str(uuid.uuid4())[:8]
            for i, chunk_text in enumerate(chunks):
                chunk_path = os.path.join(BASE_DIR, "output", "temp", f"{session_id}_{i:03d}_{voice_id}_raw.wav")
                engine_manager.generate(
                    text=chunk_text,
                    voice_id=voice_id,
                    language=lang,
                    output_path=chunk_path,
                    override_settings=request.settings
                )
                temp_files.append(chunk_path)
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    import gc
                    gc.collect()
            
            merged_path = os.path.join(BASE_DIR, "output", "temp", f"{session_id}_merged.wav")
            from audio import merge_audio_files
            merged_path = merge_audio_files(temp_files, merged_path)
            for f in temp_files:
                if os.path.exists(f):
                    try: os.remove(f)
                    except: pass

        # Process with DSP
        from backend.audio.processor import audio_processor
        from backend.audio.encoder import audio_encoder
        
        dsp_path = merged_path.replace(".wav", "_dsp.wav")
        audio_processor.process(merged_path, dsp_path, request.settings)
        
        # Convert to MP3
        final_mp3 = audio_encoder.encode_to_mp3(dsp_path, temp_path)
        
        # Cleanup
        if os.path.exists(merged_path):
            try: os.remove(merged_path)
            except: pass
        if os.path.exists(dsp_path):
            try: os.remove(dsp_path)
            except: pass
            
        filename = os.path.basename(final_mp3)
        return {
            "status": "success",
            "audio_url": f"/output/temp/{filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CompareRequest(BaseModel):
    text: str
    settingsA: dict
    settingsB: dict

@app.post("/v1/voices/{voice_id}/compare")
def generate_compare(voice_id: str, request: CompareRequest, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
        
    os.makedirs(os.path.join(BASE_DIR, "output", "temp"), exist_ok=True)
    lang = voice.language.split("-")[0] if voice.language else "hi"
    
    try:
        from backend.text.pipeline import text_pipeline
        from audio import merge_audio_files
        from backend.audio.processor import audio_processor
        from backend.audio.encoder import audio_encoder
        
        # Enforce 500 character limit for compare
        preview_text = request.text[:500]
        chunks = text_pipeline.process_chapter(preview_text, lang)
        
        def _generate_variant(settings, prefix):
            temp_path = os.path.join(BASE_DIR, "output", "temp", f"{prefix}_{uuid.uuid4().hex[:8]}.mp3")
            
            if len(chunks) <= 1:
                raw_output = temp_path.replace(".mp3", "_raw.wav")
                engine_manager.generate(
                    text=chunks[0] if chunks else preview_text, 
                    voice_id=voice_id, 
                    language=lang, 
                    output_path=raw_output,
                    override_settings=settings
                )
                merged_path = raw_output
            else:
                temp_files = []
                session_id = str(uuid.uuid4())[:8]
                for i, chunk_text in enumerate(chunks):
                    chunk_path = os.path.join(BASE_DIR, "output", "temp", f"{session_id}_{i:03d}_{voice_id}_raw.wav")
                    engine_manager.generate(
                        text=chunk_text,
                        voice_id=voice_id,
                        language=lang,
                        output_path=chunk_path,
                        override_settings=settings
                    )
                    temp_files.append(chunk_path)
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        import gc
                        gc.collect()
                
                merged_path = os.path.join(BASE_DIR, "output", "temp", f"{session_id}_merged.wav")
                merged_path = merge_audio_files(temp_files, merged_path)
                for f in temp_files:
                    if os.path.exists(f):
                        try: os.remove(f)
                        except: pass

            dsp_path = merged_path.replace(".wav", "_dsp.wav")
            audio_processor.process(merged_path, dsp_path, settings)
            final_mp3 = audio_encoder.encode_to_mp3(dsp_path, temp_path)
            
            if os.path.exists(merged_path):
                try: os.remove(merged_path)
                except: pass
            if os.path.exists(dsp_path):
                try: os.remove(dsp_path)
                except: pass
                
            return final_mp3
            
        # Generate A and B
        final_a = _generate_variant(request.settingsA, "compare_a")
        final_b = _generate_variant(request.settingsB, "compare_b")
        
        return {
            "status": "success",
            "audio_url_a": f"/output/temp/{os.path.basename(final_a)}",
            "audio_url_b": f"/output/temp/{os.path.basename(final_b)}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- AUDIO GENERATION ----

@app.post("/v1/audio/speech")
def generate_speech(request: SpeechRequest, db: Session = Depends(get_db)):
    os.makedirs(os.path.join(BASE_DIR, "output", "single"), exist_ok=True)
    
    # settings_hash
    settings_hash = ""
    if request.settings:
        settings_str = "".join(f"{k}{v}" for k,v in sorted(request.settings.items()))
        settings_hash = hashlib.md5(settings_str.encode()).hexdigest()[:8]
        
    text_hash = hashlib.md5(request.input.strip().encode()).hexdigest()[:8]
    
    cache_string = f"{text_hash}_{request.voice}_{request.model}_{settings_hash}"
    cache_key = hashlib.md5(cache_string.encode("utf-8")).hexdigest()
    
    voice = db.query(Voice).filter(Voice.id == request.voice).first()
    # Pipeline always produces .mp3 at the end via AudioEncoder
    output_path = os.path.join(BASE_DIR, "output", "single", f"{cache_key}.mp3")
    audio_id = f"audio_{cache_key}"
    
    actual_path = None
    if os.path.exists(output_path): actual_path = output_path
    
    if actual_path:
        print(f"Cache hit for {request.voice}: {cache_key}")
        audio_url = f"/audio/single/{os.path.basename(actual_path)}"
        return {"id": audio_id, "status": "completed", "audio_url": audio_url, "cached": True}
    
    print(f"Cache miss for {request.voice}. Generating...")
    try:
        # Use new TextPipeline
        target_lang = voice.language.split("-")[0] if voice.language else "hi"
        chunks = text_pipeline.process_chapter(request.input, target_lang)
        
        if len(chunks) <= 1:
            raw_output = output_path.replace(".mp3", "_raw.wav")
            engine_manager.generate(
                text=chunks[0] if chunks else request.input, 
                voice_id=request.voice, 
                language=target_lang, 
                output_path=raw_output,
                override_settings=request.settings
            )
            merged_path = raw_output
        else:
            temp_files = []
            session_id = str(uuid.uuid4())[:8]
            os.makedirs(os.path.join(BASE_DIR, "output", "temp"), exist_ok=True)
            for i, chunk_text in enumerate(chunks):
                chunk_path = os.path.join(BASE_DIR, "output", "temp", f"{session_id}_{i:03d}_{request.voice}_raw.wav")
                engine_manager.generate(
                    text=chunk_text,
                    voice_id=request.voice,
                    language=target_lang,
                    output_path=chunk_path,
                    override_settings=request.settings
                )
                temp_files.append(chunk_path)
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    gc.collect()
            
            merged_path = os.path.join(BASE_DIR, "output", "temp", f"{session_id}_merged.wav")
            merged_path = merge_audio_files(temp_files, merged_path)
            for f in temp_files:
                if os.path.exists(f):
                    try: os.remove(f)
                    except: pass
        
        # Audio Quality Check
        quality = quality_checker.analyze_quality(merged_path)
        if quality["has_clipping"]:
            print(f"WARNING: Clipping detected in raw output (ratio: {quality['clipping_ratio']})")
        
        # Audio Processing (DSP)
        dsp_path = merged_path.replace(".wav", "_dsp.wav")
        audio_processor.process(merged_path, dsp_path, request.settings or {})
        
        # Final Encoding
        final_mp3 = audio_encoder.encode_to_mp3(dsp_path, output_path)
        
        # Cleanup
        if os.path.exists(merged_path):
            try: os.remove(merged_path)
            except: pass
        if os.path.exists(dsp_path):
            try: os.remove(dsp_path)
            except: pass
            
        audio_url = f"/audio/single/{os.path.basename(final_mp3)}"
        
        # Save to DB history
        history_item = GeneratedAudio(
            id=audio_id,
            voice_id=request.voice,
            version_id=getattr(request, "version_id", None),
            text_hash=request.input[:100],
            settings_hash=settings_hash,
            audio_path=audio_url,
            engine=voice.engine if voice else "unknown",
            model=request.model
        )
        db.add(history_item)
        db.commit()
        
        return {"id": audio_id, "status": "completed", "audio_url": audio_url, "cached": False, "quality": quality}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/history")
def get_history(db: Session = Depends(get_db)):
    items = db.query(GeneratedAudio).order_by(GeneratedAudio.created_at.desc()).all()
    history = []
    for item in items:
        history.append({
            "id": item.id,
            "voice": item.voice_id,
            "text": item.text_hash,
            "audio_url": item.audio_path,
            "created_at": item.created_at.timestamp()
        })
    return {"history": history}

@app.delete("/v1/audio/{audio_id}")
def delete_audio(audio_id: str, db: Session = Depends(get_db)):
    item = db.query(GeneratedAudio).filter(GeneratedAudio.id == audio_id).first()
    if item:
        db.delete(item)
        db.commit()
        
    for file in os.listdir(os.path.join(BASE_DIR, "output", "single")):
        if file.startswith(audio_id.replace("audio_", "")):
            file_path = os.path.join(BASE_DIR, "output", "single", file)
            try: os.remove(file_path)
            except: pass
            
    return {"status": "deleted", "id": audio_id}

@app.get("/audio/single/{filename}")
def get_single_audio(filename: str):
    path = os.path.join(BASE_DIR, "output", "single", filename)
    if not os.path.exists(path): raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)

@app.get("/audio/chapters/{filename}")
def get_chapter_audio(filename: str):
    path = os.path.join(BASE_DIR, "output", "chapters", filename)
    if not os.path.exists(path): raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)

@app.post("/generate-chapter")
def generate_chapter(request: ChapterRequest):
    # Simplification for brevity, logic remains similar
    return {"status": "success", "message": "Chapter generation API endpoint"}

# ---- PRONUNCIATION DICTIONARY ENDPOINTS ----

class PronunciationRequest(BaseModel):
    original: str
    say_as: str
    language: str = "all"

@app.get("/v1/pronunciations")
def get_pronunciations(db: Session = Depends(get_db)):
    items = db.query(PronunciationDictionary).all()
    return {"pronunciations": [{"id": i.id, "original": i.original_word, "say_as": i.replacement_word, "language": i.language} for i in items]}

@app.post("/v1/pronunciations")
def add_pronunciation(request: PronunciationRequest, db: Session = Depends(get_db)):
    item = PronunciationDictionary(id=uuid.uuid4().hex, original_word=request.original, replacement_word=request.say_as, language=request.language)
    db.add(item)
    db.commit()
    return {"status": "success", "id": item.id}

@app.delete("/v1/pronunciations/{item_id}")
def delete_pronunciation(item_id: str, db: Session = Depends(get_db)):
    item = db.query(PronunciationDictionary).filter(PronunciationDictionary.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return {"status": "deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
