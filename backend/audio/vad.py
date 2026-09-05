import librosa
import soundfile as sf
import os
import glob
import numpy as np

# Ensure FFmpeg is in PATH before anything else so librosa can load any format
ffmpeg_dirs = glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ffmpeg-*-shared", "bin"))
if ffmpeg_dirs:
    os.environ["PATH"] = ffmpeg_dirs[0] + os.pathsep + os.environ.get("PATH", "")
    try:
        os.add_dll_directory(ffmpeg_dirs[0])
    except AttributeError:
        pass


class VoiceActivityDetector:
    def segment_audio(self, file_path: str, output_dir: str, top_db: int = 30) -> list[str]:
        """
        Extract multiple clean, CONTIGUOUS speech segments for XTTS multi-reference cloning.

        CRITICAL DESIGN:
        - XTTS get_conditioning_latents() accepts MULTIPLE audio_path files.
        - Passing 3-5 diverse clips gives a MUCH richer speaker representation than one clip.
        - Each clip must be a CONTIGUOUS segment (no stitching non-adjacent chunks).
        - Each clip should be 6-15 seconds of clean speech.
        - We also create one "optimal" combined clip for backwards compatibility.
        """
        try:
            y, sr = librosa.load(file_path, sr=22050)  # Standardize to 22050 Hz
            total_duration = len(y) / sr
            print(f"[VAD] Loaded {total_duration:.1f}s of audio at {sr}Hz")

            os.makedirs(output_dir, exist_ok=True)

            # Find non-silent intervals
            intervals = librosa.effects.split(y, top_db=max(20, top_db))

            if len(intervals) == 0:
                print("[VAD] No speech detected, using first 15s")
                segment = y[:sr * 15]
                segment = self._normalize(segment)
                path = os.path.join(output_dir, "reference_optimal.wav")
                sf.write(path, segment, sr)
                return [path]

            # ---- Strategy: Find the best CONTIGUOUS speech regions ----
            # Merge nearby intervals (gap < 0.3s) into continuous segments
            merged = self._merge_intervals(intervals, sr, max_gap_sec=0.3)

            # Score each merged segment by: duration (prefer 6-15s) + loudness
            candidates = []
            for start, end in merged:
                duration = (end - start) / sr
                if duration < 2.0:
                    continue  # Too short to be useful

                segment = y[start:end]
                rms = float(np.sqrt(np.mean(segment ** 2)))

                # Score: prefer 8-15 second clips with good volume
                duration_score = 1.0
                if duration < 6:
                    duration_score = duration / 6.0
                elif duration > 20:
                    duration_score = 0.8  # Still usable but not ideal

                score = rms * duration_score
                candidates.append({
                    "start": start,
                    "end": end,
                    "duration": duration,
                    "rms": rms,
                    "score": score,
                })

            if not candidates:
                # Fallback: use the longest interval
                print("[VAD] No good candidates found, using longest interval")
                longest = max(merged, key=lambda x: x[1] - x[0])
                segment = y[longest[0]:longest[1]]
                segment = self._normalize(segment)
                if len(segment) > sr * 15:
                    segment = segment[:sr * 15]
                path = os.path.join(output_dir, "reference_optimal.wav")
                sf.write(path, segment, sr)
                return [path]

            # Sort by score descending, take top 5
            candidates.sort(key=lambda x: x["score"], reverse=True)
            best = candidates[:5]

            print(f"[VAD] Found {len(candidates)} speech segments, selected top {len(best)}:")

            output_paths = []
            for i, c in enumerate(best):
                segment = y[c["start"]:c["end"]]

                # Cap at 15 seconds (XTTS max_ref_length is 30s, but shorter clips are cleaner)
                if len(segment) > sr * 15:
                    segment = segment[:sr * 15]

                segment = self._normalize(segment)

                filename = f"reference_{i:03d}.wav"
                path = os.path.join(output_dir, filename)
                sf.write(path, segment, sr)
                dur = len(segment) / sr
                print(f"  [{i}] {dur:.1f}s  RMS={c['rms']:.3f}  score={c['score']:.4f}")
                output_paths.append(path)

            # Also create the "optimal" reference (first/best clip) for backwards compat
            optimal_path = os.path.join(output_dir, "reference_optimal.wav")
            if not os.path.exists(optimal_path) or optimal_path not in output_paths:
                import shutil
                shutil.copy2(output_paths[0], optimal_path)
                if optimal_path not in output_paths:
                    output_paths.insert(0, optimal_path)

            return output_paths

        except Exception as e:
            print(f"[VAD] Segmentation failed: {e}")
            import traceback
            traceback.print_exc()
            return [file_path]  # Fallback to original

    def _merge_intervals(self, intervals, sr: int, max_gap_sec: float = 2.5):
        """Merge nearby non-silent intervals into contiguous speech regions."""
        max_gap = int(max_gap_sec * sr)
        merged = []
        current_start, current_end = intervals[0]

        for start, end in intervals[1:]:
            if start - current_end <= max_gap:
                # Close enough — merge
                current_end = end
            else:
                merged.append((current_start, current_end))
                current_start, current_end = start, end

        merged.append((current_start, current_end))
        return merged

    def _normalize(self, audio: np.ndarray, target_peak: float = 0.9) -> np.ndarray:
        """Peak-normalize audio to target level."""
        max_val = np.max(np.abs(audio))
        if max_val > 0.01:
            audio = audio * (target_peak / max_val)
        return audio


vad_processor = VoiceActivityDetector()
