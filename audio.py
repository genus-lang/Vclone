from pydub import AudioSegment
import os
import miniaudio

def merge_audio_files(file_paths: list, output_path: str):
    """
    Merges a list of wav and mp3 files sequentially.
    Since FFmpeg is blocked on this system, we use miniaudio to decode mp3s
    and we must export the final file as a .wav instead of .mp3.
    """
    if not file_paths:
        return None
        
    combined = AudioSegment.empty()
    
    for path in file_paths:
        if os.path.exists(path):
            if path.endswith('.mp3'):
                decoded = miniaudio.decode_file(path)
                audio = AudioSegment(
                    data=decoded.samples,
                    sample_width=decoded.sample_width,
                    frame_rate=decoded.sample_rate,
                    channels=decoded.nchannels
                )
            else:
                audio = AudioSegment.from_wav(path)
                
            # Add a small 200ms silence gap between chunks for natural pacing
            silence = AudioSegment.silent(duration=200)
            combined += audio + silence
            
    # Make sure output path ends with .wav
    if output_path.endswith(".mp3"):
        output_path = output_path[:-4] + ".wav"
        
    combined.export(output_path, format="wav")
    return output_path

