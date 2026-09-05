"""
Speaker Embedding Cache
=======================
Caches XTTS speaker latents (gpt_cond_latent + speaker_embedding) to disk so
they are not recomputed on every chunk. Benefits:
1. Speed: Avoids re-running get_conditioning_latents() per chunk.
2. Consistency: Every chunk of a chapter uses the EXACT same speaker
   representation — no floating-point variance between chunks.

Now supports MULTI-REFERENCE caching:
  - Cache key is derived from ALL reference files + their mtimes
  - get_conditioning_latents() is called with ALL reference paths at once
  - gpt_cond_len=30 and sound_norm_refs=True for maximum quality
"""
import os
import torch
import hashlib
import json
import time
from typing import Optional, Tuple, Dict, Any, List, Union

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "voices", "_embedding_cache")


class SpeakerEmbeddingCache:
    """Disk-persistent cache for XTTS speaker latents."""

    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self._memory_cache: Dict[str, Any] = {}

    def _cache_key(self, reference_paths: List[str]) -> str:
        """
        Generate a stable cache key from ALL reference files' paths + mtimes.
        If any reference file changes, the cache is automatically invalidated.
        """
        parts = []
        for p in sorted(reference_paths):
            try:
                mtime = os.path.getmtime(p)
                parts.append(f"{p}:{mtime}")
            except OSError:
                parts.append(p)
        raw = "|".join(parts)
        return hashlib.md5(raw.encode()).hexdigest()

    def _cache_paths(self, key: str) -> Tuple[str, str, str]:
        base = os.path.join(CACHE_DIR, key)
        return f"{base}_gpt.pt", f"{base}_spk.pt", f"{base}_meta.json"

    def get(self, reference_paths: Union[str, List[str]]) -> Optional[Dict[str, Any]]:
        if isinstance(reference_paths, str):
            reference_paths = [reference_paths]
        key = self._cache_key(reference_paths)
        if key in self._memory_cache:
            return self._memory_cache[key]
        gpt_path, spk_path, meta_path = self._cache_paths(key)
        if not (os.path.exists(gpt_path) and os.path.exists(spk_path)):
            return None
        try:
            gpt_cond_latent = torch.load(gpt_path, weights_only=True)
            speaker_embedding = torch.load(spk_path, weights_only=True)
            result = {"gpt_cond_latent": gpt_cond_latent, "speaker_embedding": speaker_embedding}
            self._memory_cache[key] = result
            print(f"[EmbeddingCache] HIT ({len(reference_paths)} refs)")
            return result
        except Exception as e:
            print(f"[EmbeddingCache] Failed to load cache: {e}")
            return None

    def save(self, reference_paths: Union[str, List[str]], gpt_cond_latent, speaker_embedding):
        if isinstance(reference_paths, str):
            reference_paths = [reference_paths]
        key = self._cache_key(reference_paths)
        gpt_path, spk_path, meta_path = self._cache_paths(key)
        try:
            torch.save(gpt_cond_latent, gpt_path)
            torch.save(speaker_embedding, spk_path)
            with open(meta_path, "w") as f:
                json.dump({
                    "reference_paths": reference_paths,
                    "num_refs": len(reference_paths),
                    "created_at": time.time(),
                }, f, indent=2)
            self._memory_cache[key] = {"gpt_cond_latent": gpt_cond_latent, "speaker_embedding": speaker_embedding}
            print(f"[EmbeddingCache] SAVED ({len(reference_paths)} refs)")
        except Exception as e:
            print(f"[EmbeddingCache] Failed to save: {e}")

    def invalidate(self, reference_paths: Union[str, List[str]]):
        if isinstance(reference_paths, str):
            reference_paths = [reference_paths]
        key = self._cache_key(reference_paths)
        gpt_path, spk_path, meta_path = self._cache_paths(key)
        for path in (gpt_path, spk_path, meta_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        self._memory_cache.pop(key, None)

    def invalidate_all(self):
        """Clear entire cache. Useful when model version changes."""
        import glob
        for f in glob.glob(os.path.join(CACHE_DIR, "*")):
            try:
                os.remove(f)
            except Exception:
                pass
        self._memory_cache.clear()
        print("[EmbeddingCache] ALL cache cleared")

    def get_or_compute(self, reference_paths: Union[str, List[str]], tts_model) -> Optional[Dict[str, Any]]:
        """
        Return cached embeddings or compute + cache them.
        Uses gpt_cond_len=30 and sound_norm_refs=True for maximum quality.
        """
        if isinstance(reference_paths, str):
            reference_paths = [reference_paths]

        # Filter to only existing files
        reference_paths = [p for p in reference_paths if os.path.exists(p)]
        if not reference_paths:
            return None

        cached = self.get(reference_paths)
        if cached is not None:
            return cached

        print(f"[EmbeddingCache] MISS — computing from {len(reference_paths)} reference(s)...")
        try:
            t0 = time.time()
            gpt_cond_latent, speaker_embedding = tts_model.get_conditioning_latents(
                audio_path=reference_paths,
                max_ref_length=30,
                gpt_cond_len=30,
                gpt_cond_chunk_len=6,
                sound_norm_refs=True,
            )
            elapsed = time.time() - t0
            print(f"[EmbeddingCache] Computed in {elapsed:.2f}s from {len(reference_paths)} refs")
            self.save(reference_paths, gpt_cond_latent, speaker_embedding)
            return {"gpt_cond_latent": gpt_cond_latent, "speaker_embedding": speaker_embedding}
        except Exception as e:
            print(f"[EmbeddingCache] Failed to compute: {e}")
            import traceback
            traceback.print_exc()
            return None


speaker_embedding_cache = SpeakerEmbeddingCache()
