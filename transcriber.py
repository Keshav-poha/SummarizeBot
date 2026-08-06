import sys
import os
import json
import torch
import whisper
from transformers import pipeline

# Local Whisper model configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

_whisper_instance = None
_summarizer_instance = None

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def load_whisper():
    global _whisper_instance
    if _whisper_instance is None:
        device = get_device()
        sys.stderr.write(f"Loading local Whisper model '{WHISPER_MODEL}' on device: {device}...\n")
        _whisper_instance = whisper.load_model(WHISPER_MODEL, device=device)
        sys.stderr.write("Whisper model loaded successfully!\n")
    return _whisper_instance

def load_summarizer():
    global _summarizer_instance
    if _summarizer_instance is None:
        device = get_device()
        sys.stderr.write(f"Loading local LLM Summarizer (facebook/bart-large-cnn) on device: {device}...\n")
        # Initialize pipeline. If device="cuda" or "mps", pass device=0 or string
        # pipeline accepts device index for cuda (0), or "mps" string, or "cpu" string
        dev_arg = 0 if device == "cuda" else device
        _summarizer_instance = pipeline("summarization", model="facebook/bart-large-cnn", device=dev_arg)
        sys.stderr.write("LLM Summarizer loaded successfully!\n")
    return _summarizer_instance

def transcribe_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
        
    model = load_whisper()
    sys.stderr.write(f"Starting local transcription for: {os.path.basename(file_path)}\n")
    result = model.transcribe(file_path)
    return result.get("text", "").strip()

def summarize_text(text: str) -> str:
    if not text.strip():
        return "No text provided to summarize."
    
    # Check if text is extremely short (under 50 words)
    if len(text.split()) < 50:
        return "The meeting was too short to generate a meaningful summary."

    summarizer = load_summarizer()
    sys.stderr.write(f"Summarizing text natively using transformers pipeline...\n")
    
    # Bart handles a max token limit. For simplicity, we truncate input if it's too long
    # (Bart max length is 1024 tokens, which is roughly ~700-800 words)
    # A robust solution would chunk it, but this is a solid start for most normal voice clips.
    # We slice by characters (approx 4 chars per token -> 3000 chars)
    truncated_text = text[:3500] 
    
    try:
        summary_result = summarizer(truncated_text, max_length=150, min_length=40, do_sample=False)
        return summary_result[0]['summary_text']
    except Exception as e:
        sys.stderr.write(f"Error during summarization: {e}\n")
        return f"Summary failed natively: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python transcriber.py <path_to_audio>"}))
        sys.exit(1)
        
    audio_path = sys.argv[1]
    
    try:
        transcript = transcribe_file(audio_path)
        summary = summarize_text(transcript) if transcript else "No speech detected."
        
        # Output ONLY JSON to stdout for Node.js to parse
        print(json.dumps({
            "transcript": transcript,
            "summary": summary
        }))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
