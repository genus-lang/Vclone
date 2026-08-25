import librosa
import soundfile as sf
import os
import numpy as np

class VoiceActivityDetector:
    def segment_audio(self, file_path: str, output_dir: str, top_db: int = 30) -> list[str]:
        """
        Segments a long audio file into smaller chunks based on silence detection.
        Returns a list of paths to the generated segments.
        """
        try:
            y, sr = librosa.load(file_path, sr=None)
            
            # Split non-silent intervals
            # librosa.effects.split returns intervals of non-silent regions
            intervals = librosa.effects.split(y, top_db=top_db)
            
            os.makedirs(output_dir, exist_ok=True)
            segment_paths = []
            
            # Group intervals into roughly 5-10 second chunks if possible
            current_chunk = []
            current_length = 0
            chunk_index = 0
            
            # Helper to save a chunk
            def save_chunk(chunk_samples, index):
                if len(chunk_samples) > 0:
                    out_path = os.path.join(output_dir, f"segment_{index:03d}.wav")
                    sf.write(out_path, chunk_samples, sr)
                    segment_paths.append(out_path)
            
            target_length = sr * 7 # Target 7 seconds per chunk
            
            for interval in intervals:
                start, end = interval
                segment = y[start:end]
                
                if current_length + len(segment) > target_length and current_length > 0:
                    # Save current chunk
                    save_chunk(np.concatenate(current_chunk), chunk_index)
                    chunk_index += 1
                    current_chunk = [segment]
                    current_length = len(segment)
                else:
                    current_chunk.append(segment)
                    current_length += len(segment)
                    
            # Save remaining
            if len(current_chunk) > 0:
                save_chunk(np.concatenate(current_chunk), chunk_index)
                
            return segment_paths
            
        except Exception as e:
            print(f"VAD segmentation failed: {e}")
            return [file_path] # Fallback to original

vad_processor = VoiceActivityDetector()
