import sys
import os
import json
import torch
import whisper
import urllib.request
import urllib.error

# Local Whisper model configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "local-llm-key")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")

_model_instance = None

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def load_model():
    global _model_instance
    if _model_instance is None:
        device = get_device()
        sys.stderr.write(f"Loading local Whisper model '{WHISPER_MODEL}' on device: {device}...\n")
        _model_instance = whisper.load_model(WHISPER_MODEL, device=device)
        sys.stderr.write("Whisper model loaded successfully!\n")
    return _model_instance

def transcribe_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
        
    model = load_model()
    sys.stderr.write(f"Starting local transcription for: {os.path.basename(file_path)}\n")
    result = model.transcribe(file_path)
    return result.get("text", "").strip()

def summarize_text(text: str) -> str:
    if not text.strip():
        return "No text provided to summarize."

    sys.stderr.write(f"Summarizing text using LLM ({LLM_MODEL}) at {LLM_BASE_URL}...\n")
    prompt = f"Please summarize the following meeting transcript accurately and concisely. Highlight any key action items if present:\n\n{text}"
    
    data = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful meeting summarization assistant."},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }).encode('utf-8')
    
    req_url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LLM_API_KEY}'
    }
    
    req = urllib.request.Request(req_url, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            return response_data['choices'][0]['message']['content'].strip()
    except urllib.error.URLError as e:
        sys.stderr.write(f"Failed to connect to LLM API: {e}\n")
        return "Summary failed: Could not reach the LLM API. Check your BASE_URL and API_KEY."
    except Exception as e:
        sys.stderr.write(f"Error during summarization: {e}\n")
        return f"Summary failed: {e}"

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
