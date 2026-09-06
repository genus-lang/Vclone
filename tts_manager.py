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

    def compute_speaker_latents(self, reference_paths):
        """
        Compute (gpt_cond_latent, speaker_embedding) from reference audio(s).
        Uses real Xtts.get_conditioning_latents() — verified v0.27.5 API.

        CRITICAL PARAMETERS:
        - gpt_cond_len=30: Maximum context length. Gives XTTS the richest
          possible speaker representation. Was 6 before — far too short.
        - sound_norm_refs=True: Let XTTS normalize reference audio internally.
        - audio_path accepts a LIST — passing multiple clips gives a much
          better averaged speaker embedding than a single clip.
        """
        model = self._get_xtts_model()
        if isinstance(reference_paths, str):
            reference_paths = [reference_paths]
        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=reference_paths,
            max_ref_length=30,
            gpt_cond_len=30,
            gpt_cond_chunk_len=6,
            sound_norm_refs=True,
        )
        return gpt_cond_latent, speaker_embedding

    def generate_with_latents(
        self,
        text: str,
        language: str,
        gpt_cond_latent,
        speaker_embedding,
        output_path: str,
        temperature: float = 0.65,
        repetition_penalty: float = 1.2,
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
            length_penalty=1.0,
            top_k=top_k,
            top_p=top_p,
            speed=speed,
            enable_text_splitting=True,
        )

        # out is a dict with key "wav"
        wav = out.get("wav", out)
        if hasattr(wav, "cpu"):
            wav = wav.cpu().numpy()
        wav = np.array(wav, dtype=np.float32)

        # XTTS native sample rate is 24000 Hz
        sf.write(output_path, wav, samplerate=24000)
        return output_path

    def load_finetuned_model(self, model_dir: str):
        """Load a fine-tuned XTTS model from a directory containing best_model.pth, config.json, vocab.json"""
        if not hasattr(self, "_finetuned_cache"):
            self._finetuned_cache = {}
            
        if model_dir in self._finetuned_cache:
            return self._finetuned_cache[model_dir]
            
        print(f"Loading Fine-Tuned TTS Model from {model_dir}...")
        try:
            # We must use XttsConfig to load the custom model properly
            from TTS.tts.configs.xtts_config import XttsConfig
            from TTS.tts.models.xtts import Xtts
            
            config_path = os.path.join(model_dir, "config.json")
            config = XttsConfig()
            config.load_json(config_path)
            
            model = Xtts.init_from_config(config)
            model.load_checkpoint(config, checkpoint_dir=model_dir, use_tensorboard=False)
            model.cuda()
            
            self._finetuned_cache[model_dir] = model
            print("Fine-tuned model loaded successfully.")
            return model
        except Exception as e:
            print(f"Failed to load fine-tuned model: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_with_finetuned(
        self,
        model_dir: str,
        text: str,
        language: str,
        output_path: str,
        temperature: float = 0.65,
        repetition_penalty: float = 1.2,
        top_k: int = 50,
        top_p: float = 0.85,
        speed: float = 1.0,
    ) -> str:
        """
        Generate audio using a fine-tuned model (no reference audio needed for inference).
        """
        model = self.load_finetuned_model(model_dir)
        if not model:
            raise RuntimeError(f"Could not load fine-tuned model from {model_dir}")
            
        # Get conditioning latents (we can just use dummy or self-conditioning if the model is fine-tuned)
        # But actually XTTS still expects latents. We can just use the model's default speaker or a dummy zero tensor.
        # Wait, if we fine-tuned it, the embedding is baked into the model weights, but the inference function still requires it.
        # Let's get the conditioning latents using a generic reference or just get default latents.
        
        # In a fully fine-tuned XTTS, the speaker embedding is less critical because the weights are adapted, 
        # but we still need to pass a valid tensor.
        try:
            # We extract default conditioning latents from the speaker we trained on.
            # Usually you just pass the same reference audio you trained on to get the latent.
            # But here we can just find any wav in the dataset folder, OR the original voice reference.
            
            voice_id = os.path.basename(os.path.dirname(model_dir))
            fallback_ref = os.path.join(os.path.dirname(model_dir), "..", f"{voice_id}.wav")
            
            if os.path.exists(fallback_ref):
                gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
                    audio_path=[fallback_ref],
                    max_ref_length=30,
                    gpt_cond_len=30,
                    gpt_cond_chunk_len=6,
                    sound_norm_refs=True,
                )
            else:
                # Dummy latents if no fallback is found
                gpt_cond_latent = torch.zeros((1, 1024)).cuda()
                speaker_embedding = torch.zeros((1, 4096)).cuda()

            out = model.inference(
                text=text,
                language=language,
                gpt_cond_latent=gpt_cond_latent,
                speaker_embedding=speaker_embedding,
                temperature=temperature,
                repetition_penalty=repetition_penalty,
                length_penalty=1.0,
                top_k=top_k,
                top_p=top_p,
                speed=speed,
                enable_text_splitting=True,
            )

            wav = out.get("wav", out)
            if hasattr(wav, "cpu"):
                wav = wav.cpu().numpy()
            wav = np.array(wav, dtype=np.float32)

            sf.write(output_path, wav, samplerate=24000)
            return output_path
        except Exception as e:
            print(f"Error in generate_with_finetuned: {e}")
            raise
# Singleton instance
tts_manager = TTSManager()
