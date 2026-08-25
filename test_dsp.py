import os
import sys

# Ensure backend modules can be imported
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from backend.audio.processor import audio_processor

def test_dsp():
    # 1. Create a dummy sine wave audio file
    try:
        from pedalboard.io import AudioFile
        import numpy as np
        
        sample_rate = 44100
        duration = 1.0 # seconds
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        # 440 Hz sine wave
        audio = np.sin(440 * 2 * np.pi * t)
        
        # Add a bit of noise so EQ works
        noise = np.random.normal(0, 0.1, len(t))
        audio = audio + noise
        
        # Shape: (channels, frames)
        audio = audio.reshape(1, -1)
        
        input_path = os.path.join(BASE_DIR, "output", "temp", "test_in.wav")
        output_path = os.path.join(BASE_DIR, "output", "temp", "test_out.wav")
        
        os.makedirs(os.path.dirname(input_path), exist_ok=True)
        
        with AudioFile(input_path, 'w', sample_rate, 1) as f:
            f.write(audio)
            
        print(f"Generated input audio: {input_path}")
        
        # 2. Process with extreme settings
        settings = {
            "pitch": 4.0, # shift up
            "warmth": 0.1, # extreme cut
            "clarity": 1.0,
            "resonance": 0.9,
            "breathiness": 1.0
        }
        
        audio_processor.process(input_path, output_path, settings)
        
        # 3. Verify output is different
        with AudioFile(input_path) as f:
            in_audio = f.read(f.frames)
            
        with AudioFile(output_path) as f:
            out_audio = f.read(f.frames)
            
        diff = np.max(np.abs(in_audio - out_audio))
        print(f"Max difference between input and output: {diff}")
        
        if diff > 0.1:
            print("SUCCESS: Audio DSP successfully applied and changed the audio file.")
        else:
            print("FAILURE: Audio was not modified significantly.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_dsp()
