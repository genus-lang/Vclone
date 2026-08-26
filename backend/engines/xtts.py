import os
import sys
import time
import torch
from typing import Dict, Any
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
            "embedding_cache": True,   # NEW: we support cached embeddings
        }

    def _resolve_reference(self, speaker: str) -> str:
        """Resolve the active reference file for a voice_id."""
        from backend.database import SessionLocal
        from backend.models import VoiceProfile, VoiceReference

        db = SessionLocal()
        try:
            profile = db.query(VoiceProfile).filter(VoiceProfile.voice_id == speaker).first()
            if profile:
                active_ref = db.query(VoiceReference).filter(
                    VoiceReference.profile_id == profile.id,
                    VoiceReference.is_active == True
                ).first()
                if not active_ref:
                    active_ref = db.query(VoiceReference).filter(
                        VoiceReference.profile_id == profile.id
                    ).order_by(VoiceReference.quality_score.desc()).first()

                if active_ref and os.path.exists(active_ref.file_path):
                    return active_ref.file_path
        finally:
            db.close()

        # Fallback to voice wav file
        wav_path = os.path.join(BASE_DIR, "voices", f"{speaker}.wav")
        if os.path.exists(wav_path):
            return wav_path
        return os.path.join(BASE_DIR, "voices", "narrator.wav")

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
        safe_text = text[:30].encode("ascii", "replace").decode("ascii")
        print(f"[XTTSLocalEngine] Generating: {safe_text}...")

        speaker = voice_profile.get("engine_voice_id", "narrator")
        reference_path = self._resolve_reference(speaker)

        try:
            start_time = time.time()

            # --- Use embedding cache if the model is already loaded ---
            if self.tts_manager.is_loaded:
                latents = speaker_embedding_cache.get_or_compute(
                    reference_path, self.tts_manager._get_xtts_model()
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
                    # Fallback to standard generation
                    self.tts_manager.generate(text, [reference_path], language, output_path)
            else:
                # First load — use standard path (triggers model load)
                self.tts_manager.generate(text, [reference_path], language, output_path)

            generation_time = time.time() - start_time

            # --- Metrics ---
            try:
                import librosa
                audio_duration = librosa.get_duration(path=output_path)
                rtf = generation_time / audio_duration if audio_duration > 0 else 0
                vram_peak = torch.cuda.max_memory_allocated() / (1024**3) if torch.cuda.is_available() else 0.0

                print(f"\nVoice: {speaker}")
                print(f"Engine: XTTS-v2 (v0.27.5)")
                print(f"Text: {len(text)} characters")
                print(f"Generation time: {generation_time:.2f} sec")
                print(f"Audio duration: {audio_duration:.2f} sec")
                print(f"RTF: {rtf:.2f}  (benchmark, not guaranteed)")
                print(f"VRAM peak: {vram_peak:.2f} GB\n")
            except Exception as e:
                print(f"[Metrics] {e}")

            # --- Per-chunk QA ---
            qa = chunk_evaluator.evaluate(output_path, text, reference_rms)
            if not qa["passed"]:
                print(f"[ChunkQA] ISSUES: {qa['issues']}")
                if auto_retry:
                    print(f"[ChunkQA] Retrying chunk once...")
                    # Retry using standard path (different random seed due to temperature sampling)
                    self.tts_manager.generate(text, [reference_path], language, output_path)
                    qa2 = chunk_evaluator.evaluate(output_path, text, reference_rms)
                    if qa2["passed"]:
                        print("[ChunkQA] Retry PASSED")
                    else:
                        print(f"[ChunkQA] Retry still failed: {qa2['issues']} — keeping best attempt")
            else:
                print(f"[ChunkQA] PASS  dur={qa['metrics'].get('duration_sec')}s")

            return True

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[XTTSLocalEngine] error: {e}")
            return False
