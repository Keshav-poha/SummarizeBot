import os
import tempfile
import time
import discord
from pydub import AudioSegment
import transcriber

def mix_audio_segments(audio_segments, encoding: str) -> str:
    """
    Overlays multiple AudioSegments into a single unified stream,
    padding shorter clips with silence to preserve synchronization.
    
    Args:
        audio_segments (list[AudioSegment]): List of Pydub AudioSegments.
        encoding (str): Target audio file extension/format.
        
    Returns:
        str: Absolute path to the mixed output file, or None if failed.
    """
    if not audio_segments:
        return None

    # Determine the duration of the longest audio track
    max_duration = max(len(segment) for segment in audio_segments)
    
    # Initialize the base segment (padded to maximum duration)
    combined = audio_segments[0]
    if len(combined) < max_duration:
        combined = combined + AudioSegment.silent(duration=max_duration - len(combined))
        
    # Overlay each of the remaining tracks
    for segment in audio_segments[1:]:
        if len(segment) < max_duration:
            segment = segment + AudioSegment.silent(duration=max_duration - len(segment))
        combined = combined.overlay(segment)
        
    # Export mixed audio to a temporary file
    temp_dir = tempfile.gettempdir()
    combined_path = os.path.join(temp_dir, f"combined_{int(time.time())}.{encoding}")
    
    try:
        combined.export(combined_path, format=encoding)
        return combined_path
    except Exception as e:
        print(f"Failed to export mixed audio: {e}")
        return None

def process_recording(sink_audio_data, encoding: str) -> tuple[str, dict[int, str]]:
    """
    Processes all captured speaker streams from a recording session.
    Saves raw bytes to disk, mixes the streams, transcribes each speaker,
    and handles cleanup of temporary files.
    
    Args:
        sink_audio_data (dict): Dict of user_id -> AudioData objects from Pycord.
        encoding (str): Audio format (e.g. 'wav').
        
    Returns:
        tuple[str, dict[int, str]]: Path to mixed audio file, and dict of user_id -> transcript.
    """
    temp_dir = tempfile.gettempdir()
    user_files = []
    
    # 1. Write each speaker's BytesIO stream to a temporary WAV file on disk
    for user_id, audio in sink_audio_data.items():
        temp_path = os.path.join(temp_dir, f"rec_{user_id}_{int(time.time())}.{encoding}")
        audio.file.seek(0)
        with open(temp_path, "wb") as f:
            f.write(audio.file.read())
        user_files.append((user_id, temp_path))
        
    if not user_files:
        return None, {}
        
    # 2. Load audio segments and mix them
    audio_segments = []
    for user_id, path in user_files:
        try:
            segment = AudioSegment.from_file(path)
            audio_segments.append(segment)
        except Exception as e:
            print(f"Error loading audio segment for user {user_id}: {e}")
            
    combined_path = mix_audio_segments(audio_segments, encoding)
    
    # 3. Transcribe each individual speaker's audio file
    transcripts = {}
    for user_id, path in user_files:
        try:
            text = transcriber.transcribe_file(path)
            if text.strip():
                transcripts[user_id] = text
        except Exception as e:
            print(f"Error transcribing user {user_id}: {e}")
            transcripts[user_id] = f"*Transcription error: {e}*"
            
    # 4. Clean up individual speaker files
    for _, path in user_files:
        try:
            os.remove(path)
        except Exception:
            pass
            
    return combined_path, transcripts
