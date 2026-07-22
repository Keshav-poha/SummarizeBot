import os
import torch
import whisper
from config import WHISPER_MODEL

# Global Whisper model variable (lazy-loaded when needed)
_model_instance = None

def get_device():
    """
    Detects the best available device for Whisper execution.
    Prefers CUDA (NVIDIA GPU) or MPS (Apple Silicon GPU) over CPU.
    """
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def load_model():
    """
    Loads the Whisper model into memory.
    Downloads the model if it hasn't been cached locally yet.
    """
    global _model_instance
    if _model_instance is None:
        device = get_device()
        print(f"Loading local Whisper model '{WHISPER_MODEL}' on device: {device}...")
        
        # Load the whisper model on the detected device
        # Note: torch.device handles the device specification
        _model_instance = whisper.load_model(WHISPER_MODEL, device=device)
        print("Whisper model loaded successfully!")
    return _model_instance

def transcribe_file(file_path: str) -> str:
    """
    Transcribes an audio file locally using the Whisper model.
    
    Args:
        file_path (str): The absolute or relative path to the audio file.
        
    Returns:
        str: The transcribed text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
        
    model = load_model()
    print(f"Starting local transcription for: {os.path.basename(file_path)}")
    
    # Run the transcription
    result = model.transcribe(file_path)
    return result.get("text", "").strip()
