import sys, os, uuid
sys.path.insert(0, '.')
from backend.database import SessionLocal
from backend.models import VoiceProfile, VoiceReference
from backend.voice.reference_manager import reference_manager
import librosa

db = SessionLocal()
voice_id = 'ayush_kumar_tiwari'

profile = db.query(VoiceProfile).filter(VoiceProfile.voice_id == voice_id).first()
if not profile:
    print('Profile not found')
    sys.exit(1)

# Delete old references
old_refs = db.query(VoiceReference).filter(VoiceReference.profile_id == profile.id).all()
print('Deleting', len(old_refs), 'old references...')
for r in old_refs:
    db.delete(r)
db.commit()

# Add new multi-segment references
seg_dir = os.path.join('voices', voice_id + '_Natural_segments')
wavs = sorted([os.path.join(seg_dir, f) for f in os.listdir(seg_dir) if f.startswith('reference_') and f.endswith('.wav')])

for i, wav_path in enumerate(wavs):
    abs_path = os.path.abspath(wav_path)
    score = reference_manager.score_reference(abs_path)
    dur = librosa.get_duration(path=abs_path)
    ref = VoiceReference(
        id=uuid.uuid4().hex,
        profile_id=profile.id,
        file_path=abs_path,
        duration=dur,
        quality_score=score.get('quality_score'),
        snr_db=score.get('snr_db'),
        speech_density=score.get('speech_density'),
        silence_ratio=score.get('silence_ratio'),
        peak_db=score.get('peak_db'),
        dynamic_range_db=score.get('dynamic_range_db'),
        has_clipping=score.get('has_clipping'),
        is_active=True,
    )
    db.add(ref)
    qs = score.get('quality_score', 0)
    snr = score.get('snr_db', 0)
    print(f'  [{i}] {os.path.basename(wav_path)}: {dur:.1f}s quality={qs}/100 SNR={snr:.1f}dB')

db.commit()
db.close()
print('Done. Added', len(wavs), 'new references.')
