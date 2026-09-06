"""
XTTS Fine-Tuning Trainer
=========================
Wraps Coqui's GPTTrainer to fine-tune XTTS-v2 on a user's voice dataset.

Usage:
    trainer = XTTSFineTuner(voice_id="my_voice")
    trainer.train(dataset_dir="voices/my_voice/dataset/", epochs=15)
    # => Saves fine-tuned model to voices/my_voice/model/

The fine-tuned checkpoint can then be loaded by TTSManager for inference,
replacing zero-shot conditioning with a permanently learned voice identity.
"""
import os
import sys
import json
import time
import shutil
import torch
import gc
from typing import Dict, Any, Optional, Callable
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pretrained XTTS-v2 model directory (downloaded by Coqui TTS)
PRETRAINED_MODEL_DIR = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "tts",
    "tts_models--multilingual--multi-dataset--xtts_v2"
)


class XTTSFineTuner:

    def __init__(self, voice_id: str):
        self.voice_id = voice_id
        self.output_dir = os.path.join(BASE_DIR, "voices", voice_id, "model")
        self.status_file = os.path.join(BASE_DIR, "voices", voice_id, "training_status.json")
        os.makedirs(self.output_dir, exist_ok=True)

    def _update_status(self, status: str, epoch: int = 0, total_epochs: int = 0,
                       loss: float = 0.0, message: str = ""):
        data = {
            "status": status,
            "epoch": epoch,
            "total_epochs": total_epochs,
            "loss": round(loss, 4),
            "message": message,
            "timestamp": time.time(),
        }
        with open(self.status_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_status(self) -> Dict[str, Any]:
        if os.path.exists(self.status_file):
            with open(self.status_file, "r") as f:
                return json.load(f)
        return {"status": "idle", "epoch": 0, "total_epochs": 0, "loss": 0, "message": "No training started"}

    def is_trained(self) -> bool:
        """Check if a fine-tuned model exists for this voice."""
        best_model = os.path.join(self.output_dir, "best_model.pth")
        return os.path.exists(best_model)

    def train(
        self,
        dataset_dir: str,
        epochs: int = 15,
        batch_size: int = 2,
        learning_rate: float = 5e-6,
        grad_accum_steps: int = 42,
        language: str = "hi",
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Fine-tune XTTS-v2 on the prepared dataset.
        
        This runs synchronously and blocks the GPU. Call from a background thread.
        """
        from TTS.tts.layers.xtts.trainer.gpt_trainer import GPTTrainer, GPTArgs, GPTTrainerConfig
        from TTS.config.shared_configs import BaseDatasetConfig
        from TTS.tts.models.xtts import XttsAudioConfig
        from TTS.tts.configs.shared_configs import CharactersConfig
        from trainer import Trainer, TrainerArgs

        self._update_status("preparing", 0, epochs, message="Preparing training configuration...")

        # Verify pretrained model files exist
        model_pth = os.path.join(PRETRAINED_MODEL_DIR, "model.pth")
        vocab_json = os.path.join(PRETRAINED_MODEL_DIR, "vocab.json")
        config_json = os.path.join(PRETRAINED_MODEL_DIR, "config.json")
        
        # DVAE and mel_stats might be in different locations
        dvae_pth = os.path.join(PRETRAINED_MODEL_DIR, "dvae.pth")
        mel_stats = os.path.join(PRETRAINED_MODEL_DIR, "mel_stats.pth")

        for fpath in [model_pth, vocab_json, config_json]:
            if not os.path.exists(fpath):
                error_msg = f"Missing pretrained file: {fpath}"
                self._update_status("error", message=error_msg)
                raise FileNotFoundError(error_msg)

        metadata_path = os.path.join(dataset_dir, "metadata.csv")
        if not os.path.exists(metadata_path):
            error_msg = f"No metadata.csv found in {dataset_dir}"
            self._update_status("error", message=error_msg)
            raise FileNotFoundError(error_msg)

        # Run dir for this training session
        run_dir = os.path.join(self.output_dir, "run")
        os.makedirs(run_dir, exist_ok=True)

        print(f"[Trainer] Starting fine-tuning for voice '{self.voice_id}'")
        print(f"[Trainer] Dataset: {dataset_dir}")
        print(f"[Trainer] Epochs: {epochs}, Batch: {batch_size}, LR: {learning_rate}")
        print(f"[Trainer] Output: {self.output_dir}")

        try:
            # Dataset config
            dataset_config = BaseDatasetConfig(
                formatter="ljspeech",
                dataset_name=f"voice_{self.voice_id}",
                path=dataset_dir,
                meta_file_train="metadata.csv",
                language=language,
            )

            # Training config
            training_config = GPTTrainerConfig(
                output_path=run_dir,
                model_args=GPTArgs(
                    max_conditioning_length=132300,
                    min_conditioning_length=66150,
                    debug_loading_failures=False,
                    max_wav_length=255995,
                    max_text_length=200,
                    mel_norm_file=mel_stats if os.path.exists(mel_stats) else None,
                    dvae_checkpoint=dvae_pth if os.path.exists(dvae_pth) else None,
                    xtts_checkpoint=model_pth,
                    tokenizer_file=vocab_json,
                    gpt_num_audio_tokens=1026,
                    gpt_start_audio_token=1024,
                    gpt_stop_audio_token=1025,
                ),
                audio=XttsAudioConfig(sample_rate=22050, dvae_sample_rate=22050, output_sample_rate=24000),
                batch_size=batch_size,
                eval_batch_size=batch_size,
                num_loader_workers=0,  # Windows compatibility
                epochs=epochs,
                lr=learning_rate,
                optimizer="AdamW",
                optimizer_params={"betas": [0.9, 0.96], "eps": 1e-8, "weight_decay": 1e-2},
                lr_scheduler="StepLR",
                lr_scheduler_params={"step_size": 50, "gamma": 0.5, "last_epoch": -1},
                grad_clip=[1000.0],
                run_eval=False,  # Skip eval to save time
                print_step=25,
                save_step=1000,
                save_n_checkpoints=2,
                save_checkpoints=True,
                save_all_best=True,
                dashboard_logger="",
                datasets=[dataset_config],
            )

            self._update_status("training", 0, epochs, message="Training started...")

            # Initialize trainer
            model = GPTTrainer.init_from_config(training_config)
            
            from TTS.tts.datasets import load_tts_samples
            try:
                train_samples, eval_samples = load_tts_samples(
                    dataset_config,
                    eval_split=True,
                    eval_split_max_size=training_config.eval_split_max_size,
                    eval_split_size=0.15,
                )
            except Exception as e:
                print(f"[Trainer] Eval split failed ({e}), using no eval split.")
                train_samples, _ = load_tts_samples(dataset_config, eval_split=False)
                eval_samples = None
            
            trainer = Trainer(
                TrainerArgs(
                    restore_path=None,
                    skip_train_epoch=False,
                    start_with_eval=False,
                    grad_accum_steps=grad_accum_steps,
                ),
                training_config,
                output_path=run_dir,
                model=model,
                train_samples=train_samples,
                eval_samples=eval_samples,
            )

            # Run training
            trainer.fit()

            self._update_status("saving", epochs, epochs, message="Saving best model...")

            # Find and copy the best checkpoint
            best_model_path = self._find_best_checkpoint(run_dir)
            if best_model_path:
                dest = os.path.join(self.output_dir, "best_model.pth")
                shutil.copy2(best_model_path, dest)
                # Also copy vocab and config for standalone loading
                shutil.copy2(vocab_json, os.path.join(self.output_dir, "vocab.json"))
                shutil.copy2(config_json, os.path.join(self.output_dir, "config.json"))
                print(f"[Trainer] Best model saved to {dest}")
            else:
                print("[Trainer] WARNING: No best checkpoint found, using latest")

            self._update_status("complete", epochs, epochs, message="Training complete! Premium voice ready.")

            # Cleanup VRAM
            del model, trainer
            torch.cuda.empty_cache()
            gc.collect()

            return {
                "status": "complete",
                "model_path": self.output_dir,
                "epochs": epochs,
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            self._update_status("error", message=str(e))
            # Cleanup VRAM on error too
            torch.cuda.empty_cache()
            gc.collect()
            raise

    def _find_best_checkpoint(self, run_dir: str) -> Optional[str]:
        """Find the best checkpoint file in the training run directory."""
        # Coqui trainer saves best models with 'best_model' in the name
        for root, dirs, files in os.walk(run_dir):
            for f in sorted(files, reverse=True):
                if "best_model" in f and f.endswith(".pth"):
                    return os.path.join(root, f)

        # Fallback: find the latest checkpoint
        for root, dirs, files in os.walk(run_dir):
            pth_files = [f for f in files if f.endswith(".pth")]
            if pth_files:
                pth_files.sort(reverse=True)
                return os.path.join(root, pth_files[0])

        return None
