# Discord Voice Recording & Local Transcription Bot

A modular, python-based Discord bot designed for Linux servers (such as a Hetzner VPS box running Ubuntu/Debian) that joins voice channels, records conversations, merges individual speaker streams, and transcribes speech locally using OpenAI's Whisper model (100% private and free).

---

## Codebase Architecture
The project is split into separate modules for clean separation of concerns:
- [bot.py](file:///c:/Projects/SummarizeBot/bot.py): Main entry point; initializes Pycord and registers application (slash) commands.
- [config.py](file:///c:/Projects/SummarizeBot/config.py): Loads and validates settings from the `.env` file.
- [transcriber.py](file:///c:/Projects/SummarizeBot/transcriber.py): Manages local Whisper model lazy loading and audio transcription. Automatically detects the best backend (CUDA/GPU or CPU).
- [audio_processor.py](file:///c:/Projects/SummarizeBot/audio_processor.py): Coordinates stream writing, overlays speaker audio, and orchestrates transcription.

---

## Features
- **Multi-user Recording**: Pycord records separate audio streams for every speaker in the channel.
- **Audio Mixing**: Combines individual speaker streams into a single synchronized `.wav` track using Pydub, padding silence dynamically.
- **Local Transcription (Private & Free)**: Runs local Whisper models on your system. On GPU-enabled servers, this automatically leverages NVIDIA CUDA. On standard CPU servers, it runs on optimized CPU threads.
- **Asynchronous Execution**: Merging and transcription tasks are performed on a thread executor so that the Discord bot remains responsive.
- **Diarized Output**: Attributes transcripts to each speaker directly.
- **Privacy Notice**: Automatically notifies users of the recording when it starts.

---

## Prerequisites (Hetzner Linux VPS Setup)

### 1. Update Packages & Install System Requirements
The bot requires `ffmpeg`, `python3`, `python3-pip`, `python3-venv`, and `git`. On a Debian/Ubuntu-based Hetzner box, run:
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3 python3-pip python3-venv git
```

---

## Installation & Setup

1. **Clone the Repository**
   On your Hetzner box, clone this repository:
   ```bash
   git clone https://github.com/Keshav-poha/SummarizeBot.git
   cd SummarizeBot
   ```

2. **Run the Automated Setup & Run Script**
   We have provided a unified script that handles dependencies installation, virtualenv setup, bot token configuration, and prints your bot's Server Invite Link:
   ```bash
   bash setup_and_run.sh
   ```

### Manual Installation alternative:
If you prefer to set up manually:
1. **Create and Activate a Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment Variables**
   Create a `.env` file from the template:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in:
   - `DISCORD_TOKEN`: Your Discord Bot Token (see developer portal guide below).
   - `WHISPER_MODEL`: The local model size (e.g., `tiny`, `base`, `small`, `medium`). `base` is recommended for standard CPU VMs.

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

- **Hardware Acceleration**: PyTorch will run local Whisper models using NVIDIA CUDA if an Nvidia GPU is available on the Hetzner box. On standard CPU-only VPS instances, it runs on optimized CPU threads.
- **Asynchronous Execution**: Audio merging and Whisper transcription run in a separate thread pool (`loop.run_in_executor`) to prevent blocking the Discord WebSocket heartbeat, avoiding disconnects during long transcriptions.
