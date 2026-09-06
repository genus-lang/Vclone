"""
Dataset Builder for XTTS Fine-Tuning
=====================================
Takes a raw audio file, transcribes it with Whisper, segments it using
word-level timestamps, and outputs an LJSpeech-format dataset.

Output:
    voices/{voice_id}/dataset/
        wavs/
            0001.wav
            0002.wav
            ...
        metadata.csv   (filename|text|text)
"""
import os
import csv
import numpy as np
import soundfile as sf
import librosa
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DatasetBuilder:

    def __init__(self, whisper_model_size: str = "medium"):
        self.whisper_model_size = whisper_model_size
        self._whisper_model = None

    def _get_whisper(self):
        """Lazy-load Whisper model to avoid VRAM usage until needed."""
        if self._whisper_model is None:
            from faster_whisper import WhisperModel
            print(f"[DatasetBuilder] Loading Whisper '{self.whisper_model_size}'...")
            self._whisper_model = WhisperModel(
                self.whisper_model_size,
                device="cuda",
                compute_type="float16"
            )
            print("[DatasetBuilder] Whisper loaded.")
        return self._whisper_model

    def build_dataset(
        self,
        audio_path: str,
        voice_id: str,
        language: str = "hi",
        min_clip_sec: float = 3.0,
        max_clip_sec: float = 15.0,
        target_sr: int = 22050,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Build an LJSpeech-format dataset from a raw audio file.

        Returns:
            {
                "dataset_dir": str,
                "num_clips": int,
                "total_duration_sec": float,
                "metadata_path": str,
            }
        """
        dataset_dir = os.path.join(BASE_DIR, "voices", voice_id, "dataset")
        wavs_dir = os.path.join(dataset_dir, "wavs")
        os.makedirs(wavs_dir, exist_ok=True)
        metadata_path = os.path.join(dataset_dir, "metadata.csv")

        if progress_callback:
            progress_callback("transcribing", 0, "Transcribing audio with Whisper...")

        # Step 1: Transcribe with word-level timestamps
        whisper = self._get_whisper()
        segments_iter, info = whisper.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )
        # Materialize the generator
        segments = list(segments_iter)
        print(f"[DatasetBuilder] Whisper detected language: {info.language} (prob={info.language_probability:.2f})")
        print(f"[DatasetBuilder] Found {len(segments)} segments from Whisper")

        if progress_callback:
            progress_callback("transcribing", 50, f"Found {len(segments)} speech segments")

        # Step 2: Load full audio
        y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
        total_audio_duration = len(y) / sr

        if progress_callback:
            progress_callback("segmenting", 60, "Segmenting audio into training clips...")

        # Step 3: Group Whisper segments into clips of ideal length
        clips = self._group_segments_into_clips(
            segments, min_clip_sec, max_clip_sec
        )
        print(f"[DatasetBuilder] Grouped into {len(clips)} training clips")

        # Step 4: Extract and save each clip
        metadata_rows = []
        total_clip_duration = 0.0

        for i, clip in enumerate(clips):
            start_sample = int(clip["start"] * target_sr)
            end_sample = int(clip["end"] * target_sr)

            # Clamp to audio bounds
            start_sample = max(0, start_sample)
            end_sample = min(len(y), end_sample)

            clip_audio = y[start_sample:end_sample]
            clip_duration = len(clip_audio) / target_sr

            if clip_duration < min_clip_sec * 0.5:
                continue  # Skip clips that are too short

            # Normalize volume
            peak = np.max(np.abs(clip_audio))
            if peak > 0:
                clip_audio = clip_audio * (0.9 / peak)

            # Save clip
            filename = f"{i+1:04d}.wav"
            clip_path = os.path.join(wavs_dir, filename)
            sf.write(clip_path, clip_audio, target_sr)

            # Clean up text
            text = clip["text"].strip()
            if text:
                metadata_rows.append((filename.replace(".wav", ""), text, text))
                total_clip_duration += clip_duration

            if progress_callback:
                pct = 60 + int(35 * (i + 1) / len(clips))
                progress_callback("segmenting", pct, f"Processed clip {i+1}/{len(clips)}")

        # Step 5: Write metadata.csv
        with open(metadata_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="|", quoting=csv.QUOTE_NONE, escapechar="\\")
            for row in metadata_rows:
                writer.writerow(row)

        if progress_callback:
            progress_callback("complete", 100, f"Dataset ready: {len(metadata_rows)} clips, {total_clip_duration:.1f}s")

        result = {
            "dataset_dir": dataset_dir,
            "num_clips": len(metadata_rows),
            "total_duration_sec": round(total_clip_duration, 1),
            "total_audio_duration_sec": round(total_audio_duration, 1),
            "metadata_path": metadata_path,
        }
        print(f"[DatasetBuilder] Dataset ready: {result}")
        return result

    def _group_segments_into_clips(
        self,
        segments,
        min_clip_sec: float,
        max_clip_sec: float,
    ) -> List[Dict[str, Any]]:
        """
        Group Whisper segments into clips of ideal duration.
        Tries to respect sentence boundaries.
        """
        clips = []
        current_clip = {"start": None, "end": None, "text": ""}

        for seg in segments:
            seg_start = seg.start
            seg_end = seg.end
            seg_text = seg.text.strip()

            if not seg_text:
                continue

            if current_clip["start"] is None:
                # Start a new clip
                current_clip["start"] = seg_start
                current_clip["end"] = seg_end
                current_clip["text"] = seg_text
            else:
                potential_duration = seg_end - current_clip["start"]

                if potential_duration <= max_clip_sec:
                    # Add to current clip
                    current_clip["end"] = seg_end
                    current_clip["text"] += " " + seg_text
                else:
                    # Current clip is long enough, save it
                    clip_duration = current_clip["end"] - current_clip["start"]
                    if clip_duration >= min_clip_sec:
                        clips.append(dict(current_clip))

                    # Start new clip with this segment
                    current_clip = {
                        "start": seg_start,
                        "end": seg_end,
                        "text": seg_text,
                    }

        # Don't forget the last clip
        if current_clip["start"] is not None:
            clip_duration = current_clip["end"] - current_clip["start"]
            if clip_duration >= min_clip_sec:
                clips.append(dict(current_clip))

        return clips

    def unload_whisper(self):
        """Free Whisper VRAM before training starts."""
        if self._whisper_model is not None:
            del self._whisper_model
            self._whisper_model = None
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
            print("[DatasetBuilder] Whisper unloaded from VRAM")


dataset_builder = DatasetBuilder()
