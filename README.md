# Discord Voice Recording & Local Transcription Bot

A modular, python-based Discord bot designed for macOS (and other platforms) that joins voice channels, records conversations, merges individual speaker streams, and transcribes speech locally using OpenAI's Whisper model (100% private and free).

---

## Codebase Architecture
The project is split into separate modules for clean separation of concerns:
- [bot.py](file:///c:/Projects/SummarizeBot/bot.py): Main entry point; initializes Pycord and registers application (slash) commands.
- [config.py](file:///c:/Projects/SummarizeBot/config.py): Loads and validates settings from the `.env` file.
- [transcriber.py](file:///c:/Projects/SummarizeBot/transcriber.py): Manages local Whisper model lazy loading and audio transcription. Automatically detects the best backend (MPS/GPU or CPU).
- [audio_processor.py](file:///c:/Projects/SummarizeBot/audio_processor.py): Coordinates stream writing, overlays speaker audio, and orchestrates transcription.

---

## Features
- **Multi-user Recording**: PYcord records separate audio streams for every speaker in the channel.
- **Audio Mixing**: Combines individual speaker streams into a single synchronized `.wav` track using Pydub, padding silence dynamically.
- **Local Transcription (Private & Free)**: Runs local Whisper models on your system. On macOS, this automatically leverages Apple Silicon (M1/M2/M3) GPU acceleration (MPS backend) for high-performance transcription.
- **Asynchronous Execution**: Merging and transcription tasks are performed on a thread executor so that the Discord bot remains responsive.
- **Diarized Output**: Attributes transcripts to each speaker directly.
- **Privacy Notice**: Automatically notifies users of the recording when it starts.

---

## Prerequisites (macOS Setup)

### 1. Install FFmpeg
The bot requires `ffmpeg` to process audio files. On macOS, install it using [Homebrew](https://brew.sh/):
```bash
brew install ffmpeg
```

### 2. Set Up Python
macOS comes with Python 3, but you can also update/install it using Homebrew:
```bash
brew install python
```

---

## Installation & Setup

1. **Navigate to the Project Directory**
   ```bash
   cd c:/Projects/SummarizeBot
   ```

2. **Create a Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *Note: On your first local transcription, PyTorch will automatically download the specified Whisper model from Hugging Face.*

4. **Configure Environment Variables**
   Copy the example environment configuration to `.env`:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in:
   - `DISCORD_TOKEN`: Your Discord Bot Token (see portal setup guide below).
   - `WHISPER_MODEL`: The local model size (e.g., `tiny`, `base`, `small`, `medium`). `base` is recommended for standard setups.

---

## Discord Developer Portal Setup

To run the bot, you must create a Discord Bot Application:

1. Visit the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** and give it a name (e.g., "SummarizeBot").
3. Navigate to the **Bot** tab on the left sidebar:
   - Click **Add Bot** and confirm.
   - Under **Token**, click **Reset Token** and copy the generated token. Paste this into your `.env` file as `DISCORD_TOKEN`.
   - Scroll down to **Privileged Gateway Intents** and enable **Guild Members Intent** and **Message Content Intent**.
4. Navigate to the **OAuth2** tab:
   - Under **OAuth2 URL Generator**, select the `bot` and `applications.commands` scopes.
   - Under **Bot Permissions**, check:
     - **Send Messages**
     - **Attach Files**
     - **Connect** (Voice Channel permission)
     - **Speak** (Voice Channel permission)
   - Copy the generated URL and paste it into a browser tab to invite the bot to your Discord server.

---

## Usage

1. Start the bot:
   ```bash
   python bot.py
   ```
2. When the bot is online, join a voice channel in your Discord server.
3. Use the following slash commands in any text channel the bot has access to:
   - `/join`: Joins the voice channel you are currently in.
   - `/record`: Joins your voice channel and starts recording.
   - `/stop`: Stops the recording, compiles the audio, generates the transcript, and sends both back to the chat.
   - `/leave`: Stops recording (if active) and disconnects the bot from the voice channel.

---

## Technical Details

- **Apple Silicon Acceleration (MPS)**: PyTorch will execute the Whisper model on Apple Silicon Metal Performance Shaders (MPS) to speed up transcription times if you are running on an M-series Mac.
- **Asynchronous Execution**: Audio merging and Whisper transcription run in a separate thread pool (`loop.run_in_executor`) to prevent blocking the Discord WebSocket heartbeat, avoiding disconnects during long transcriptions.
