import os
import sys
import time
import torch
from typing import Dict, Any, List
from .base import TTSEngine

# Resolve paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from tts_manager import TTSManager
from backend.voice.speaker_embedding import speaker_embedding_cache
from backend.evaluation.chunk_evaluator import chunk_evaluator


class XTTSLocalEngine(TTSEngine):
    def __init__(self):
        self.tts_manager = TTSManager()

    def capabilities(self) -> Dict[str, bool]:
        return {
            "stability": False,
            "similarity": False,
            "style": False,
            "speed": True,
            "pitch": True,
            "volume": False,
            "speaker_boost": False,
            "embedding_cache": True,
            "multi_reference": True,
        }

    def _resolve_all_references(self, speaker: str) -> List[str]:
        """
        Resolve ALL reference files for a voice_id (not just one).
        XTTS produces dramatically better clones when given multiple
        diverse clips — get_conditioning_latents() averages across them.
        """
        from backend.database import SessionLocal
        from backend.models import VoiceProfile, VoiceReference

        db = SessionLocal()
        paths = []
        try:
            profiles = db.query(VoiceProfile).filter(VoiceProfile.voice_id == speaker).all()
            for profile in profiles:
                refs = db.query(VoiceReference).filter(
                    VoiceReference.profile_id == profile.id
                ).order_by(VoiceReference.quality_score.desc()).all()
                for ref in refs:
                    if ref.file_path and os.path.exists(ref.file_path):
                        paths.append(ref.file_path)
        finally:
            db.close()

        if paths:
            print(f"[XTTS] Found {len(paths)} reference files for '{speaker}'")
            return paths

        # Fallback: look for segment files on disk
        segment_dirs = [
            os.path.join(BASE_DIR, "voices", f"{speaker}_Natural_segments"),
            os.path.join(BASE_DIR, "voices", f"{speaker}_segments"),
        ]
        for d in segment_dirs:
            if os.path.isdir(d):
                wavs = sorted([
                    os.path.join(d, f) for f in os.listdir(d)
                    if f.endswith(".wav") and os.path.getsize(os.path.join(d, f)) > 10000
                ])
                if wavs:
                    print(f"[XTTS] Found {len(wavs)} segment files in {d}")
                    return wavs

        # Last resort: single wav file
        wav_path = os.path.join(BASE_DIR, "voices", f"{speaker}.wav")
        if os.path.exists(wav_path):
            print(f"[XTTS] Using single fallback: {wav_path}")
            return [wav_path]
        narrator_path = os.path.join(BASE_DIR, "voices", "narrator.wav")
        if os.path.exists(narrator_path):
            return [narrator_path]
        return []

    def generate(
        self,
        text: str,
        voice_profile: Dict[str, Any],
        settings: Dict[str, Any],
        language: str,
        output_path: str,
        reference_rms: float = None,
        auto_retry: bool = True,
    ) -> bool:
        safe_text = text[:40].encode("ascii", "replace").decode("ascii")
        print(f"[XTTS] Generating: {safe_text}...")

        speaker = voice_profile.get("engine_voice_id", "narrator")
        reference_paths = self._resolve_all_references(speaker)

        if not reference_paths:
            print(f"[XTTS] ERROR: No reference files found for '{speaker}'")
            return False

        try:
            start_time = time.time()

            # --- Use embedding cache with ALL references ---
            if self.tts_manager.is_loaded:
                latents = speaker_embedding_cache.get_or_compute(
                    reference_paths, self.tts_manager._get_xtts_model()
                )
                if latents:
                    speed = float(settings.get("speed", 1.0)) if settings else 1.0
                    self.tts_manager.generate_with_latents(
                        text=text,
                        language=language,
                        gpt_cond_latent=latents["gpt_cond_latent"],
                        speaker_embedding=latents["speaker_embedding"],
                        output_path=output_path,
                        speed=speed,
                    )
                else:
                    self.tts_manager.generate(text, reference_paths, language, output_path)
            else:
                # First call — triggers model load, then uses multi-ref
                self.tts_manager.generate(text, reference_paths, language, output_path)

            generation_time = time.time() - start_time

            # --- Metrics ---
            try:
                import librosa
                audio_duration = librosa.get_duration(path=output_path)
                rtf = generation_time / audio_duration if audio_duration > 0 else 0
                vram_peak = torch.cuda.max_memory_allocated() / (1024**3) if torch.cuda.is_available() else 0.0

                print(f"\n  Voice: {speaker} ({len(reference_paths)} refs)")
                print(f"  Engine: XTTS-v2 | temp=0.3 | gpt_cond_len=30")
                print(f"  Text: {len(text)} chars")
                print(f"  Time: {generation_time:.2f}s | Audio: {audio_duration:.2f}s | RTF: {rtf:.2f}")
                print(f"  VRAM: {vram_peak:.2f} GB\n")
            except Exception as e:
                print(f"[Metrics] {e}")

            # --- Per-chunk QA ---
            qa = chunk_evaluator.evaluate(output_path, text, reference_rms)
            if not qa["passed"]:
                print(f"[ChunkQA] ISSUES: {qa['issues']}")
                if auto_retry:
                    print(f"[ChunkQA] Retrying with standard generation...")
                    self.tts_manager.generate(text, reference_paths[:1], language, output_path)
                    qa2 = chunk_evaluator.evaluate(output_path, text, reference_rms)
                    if qa2["passed"]:
                        print("[ChunkQA] Retry PASSED")
                    else:
                        print(f"[ChunkQA] Retry issues: {qa2['issues']}")
            else:
                print(f"[ChunkQA] PASS  dur={qa['metrics'].get('duration_sec')}s")

            return True

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[XTTS] Error: {e}")
            return False
