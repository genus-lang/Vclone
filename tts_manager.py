import os
import glob
import torch
import soundfile as sf
import numpy as np

# Ensure FFmpeg is in PATH before anything else
ffmpeg_dirs = glob.glob(os.path.join(os.path.dirname(__file__), "ffmpeg-*-shared", "bin"))
if ffmpeg_dirs:
    os.environ["PATH"] = ffmpeg_dirs[0] + os.pathsep + os.environ.get("PATH", "")
    try:
        os.add_dll_directory(ffmpeg_dirs[0])
    except AttributeError:
        pass

from TTS.api import TTS


class TTSManager:
    def __init__(self):
        self.model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts = None
        self.is_loaded = False

    def load_model(self):
        if not self.is_loaded:
            print(f"Loading TTS Model to {self.device}...")
            self.tts = TTS(
                model_name=self.model_name,
                progress_bar=False
            ).to(self.device)
            self.is_loaded = True
            print("Model loaded successfully.")

    def _get_xtts_model(self):
        """Return underlying Xtts model for low-level access."""
        if not self.is_loaded:
            self.load_model()
        return self.tts.synthesizer.tts_model

    def generate(self, text: str, speaker_wav, language: str, output_path: str):
        """Standard high-level generation. Backwards compatible."""
        if not self.is_loaded:
            self.load_model()
        safe_text = text[:30].encode('ascii', 'replace').decode('ascii')
        print(f"Generating audio for: {safe_text}...")
        self.tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path=output_path
        )
        return output_path

    def compute_speaker_latents(self, reference_path: str):
        """
        Compute (gpt_cond_latent, speaker_embedding) from reference audio.
        Uses real Xtts.get_conditioning_latents() — verified v0.27.5 API.
        """
        model = self._get_xtts_model()
        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=[reference_path],
            max_ref_length=30,
            gpt_cond_len=6,
            gpt_cond_chunk_len=6,
        )
        return gpt_cond_latent, speaker_embedding

    def generate_with_latents(
        self,
        text: str,
        language: str,
        gpt_cond_latent,
        speaker_embedding,
        output_path: str,
        temperature: float = 0.75,
        repetition_penalty: float = 10.0,
        top_k: int = 50,
        top_p: float = 0.85,
        speed: float = 1.0,
    ) -> str:
        """
        Low-level generation using pre-computed speaker latents.
        Avoids recomputing speaker embeddings per chunk — consistent voice across chunks.
        Uses real Xtts.inference() signature (verified v0.27.5).
        """
        if not self.is_loaded:
            self.load_model()

        model = self._get_xtts_model()
        out = model.inference(
            text=text,
            language=language,
            gpt_cond_latent=gpt_cond_latent,
            speaker_embedding=speaker_embedding,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            top_k=top_k,
            top_p=top_p,
            speed=speed,
            enable_text_splitting=False,
        )

        # out is a dict with key "wav"
        wav = out.get("wav", out)
        if hasattr(wav, "cpu"):
            wav = wav.cpu().numpy()
        wav = np.array(wav, dtype=np.float32)

        # XTTS native sample rate is 24000 Hz
        sf.write(output_path, wav, samplerate=24000)
        return output_path


# Singleton instance
tts_manager = TTSManager()
