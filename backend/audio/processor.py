import os
import numpy as np

try:
    from pedalboard import (
        Pedalboard, PitchShift, HighShelfFilter, LowShelfFilter, 
        Compressor, PeakFilter, NoiseGate, Gain
    )
    from pedalboard.io import AudioFile
    HAS_PEDALBOARD = True
except ImportError:
    HAS_PEDALBOARD = False

class AudioProcessor:
    def process(self, input_path: str, output_path: str, settings: dict):
        """
        Applies DSP effects (pitch, warmth, clarity, resonance) using Pedalboard.
        Non-destructive: reads input_path and writes to output_path.
        """
        if not HAS_PEDALBOARD or not os.path.exists(input_path):
            # Fallback: just copy or rename if pedalboard is missing
            if input_path != output_path:
                import shutil
                shutil.copy2(input_path, output_path)
            return

        try:
            with AudioFile(input_path) as f:
                audio = f.read(f.frames)
                samplerate = f.samplerate

            # Build the effect chain based on settings
            board = Pedalboard([])
            
            # 1. Pitch Shifting (semitones)
            pitch = settings.get("pitch", 0.0)
            if pitch != 0.0:
                board.append(PitchShift(semitones=pitch))
                
            # 2. Warmth (Low shelf boost + High shelf cut)
            warmth = settings.get("warmth", 0.5) # 0.0 to 1.0 (0.5 is neutral)
            if warmth != 0.5:
                # Map 0.0-1.0 to -6dB to +6dB
                warmth_db = (warmth - 0.5) * 12.0
                board.append(LowShelfFilter(cutoff_frequency_hz=250.0, gain_db=warmth_db))
                # Slight high cut for warmer sound, high boost for cooler sound
                board.append(HighShelfFilter(cutoff_frequency_hz=4000.0, gain_db=-warmth_db * 0.5))
                
            # 3. Clarity (High shelf boost + Compression)
            clarity = settings.get("clarity", 0.8) # default 0.8 (slightly crisp)
            if clarity != 0.5:
                clarity_db = (clarity - 0.5) * 8.0
                board.append(HighShelfFilter(cutoff_frequency_hz=3000.0, gain_db=clarity_db))
                
            # 4. Resonance (Peak filter in low-mids)
            resonance = settings.get("resonance", 0.5)
            if resonance != 0.5:
                res_db = (resonance - 0.5) * 10.0
                board.append(PeakFilter(cutoff_frequency_hz=500.0, gain_db=res_db, q=1.0))
                
            # 5. Breathiness (High end boost + slight noise - difficult to simulate perfectly, but EQ helps)
            breathiness = settings.get("breathiness", 0.1)
            if breathiness > 0.1:
                breath_db = (breathiness - 0.1) * 15.0
                board.append(HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=breath_db))
                
            # 6. Dynamics / Compression (apply light compression to glue it together)
            board.append(Compressor(threshold_db=-15, ratio=2.5, attack_ms=5, release_ms=50))
            
            # 7. Normalize Loudness (Gain compensation)
            # Find peak of dry audio
            dry_peak = np.max(np.abs(audio))
            if dry_peak == 0: dry_peak = 0.01
            
            processed = board(audio, samplerate)
            
            wet_peak = np.max(np.abs(processed))
            if wet_peak > 0:
                # Normalize to -1 dB
                target_peak = 10 ** (-1.0 / 20)
                processed = processed * (target_peak / wet_peak)
                
            # Write to output
            with AudioFile(output_path, 'w', samplerate, processed.shape[0]) as f:
                f.write(processed)
                
            print(f"[AudioProcessor] Successfully applied DSP to {output_path}")
            
        except Exception as e:
            print(f"[AudioProcessor] Failed to process audio: {e}")
            if input_path != output_path:
                import shutil
                shutil.copy2(input_path, output_path)

audio_processor = AudioProcessor()
