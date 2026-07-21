# Discord Voice Recording & Local Transcription Bot

*Last updated recently.*

A modular, python-based Discord bot tailored for Linux VPS boxes (such as **Contabo**, **Hetzner**, **DigitalOcean**, or **AWS EC2** running Ubuntu/Debian). It joins voice channels, records multi-user conversations, overlays speaker streams, and transcribes speech locally using OpenAI's Whisper model (100% private, free, and self-hosted).

---

## 🏗️ Codebase Architecture

- [bot.py](file:///c:/Projects/SummarizeBot/bot.py): Discord bot entry point using Pycord with slash commands (`/join`, `/record`, `/stop`, `/leave`).
- [transcriber.py](file:///c:/Projects/SummarizeBot/transcriber.py): Manages local Whisper model lazy loading and audio transcription (CUDA/GPU or CPU auto-detect).
- [audio_processor.py](file:///c:/Projects/SummarizeBot/audio_processor.py): Merges speaker audio tracks into synchronized `.wav` files using Pydub.
- [config.py](file:///c:/Projects/SummarizeBot/config.py): Environment configuration and validation.
- [setup_and_run.sh](file:///c:/Projects/SummarizeBot/setup_and_run.sh): Automated one-command setup script for Linux VPS.
- [create_service.sh](file:///c:/Projects/SummarizeBot/create_service.sh): Generates a 24/7 systemd background service for VPS.
- [Dockerfile](file:///c:/Projects/SummarizeBot/Dockerfile) & [docker-compose.yml](file:///c:/Projects/SummarizeBot/docker-compose.yml): Containerized deployment support.

---

## 🚀 Quick Setup on Contabo VPS (Ubuntu / Debian)

### 1. Clone the Repository
Connect to your Contabo server via SSH and clone the repository:
```bash
git clone https://github.com/Keshav-poha/SummarizeBot.git
cd SummarizeBot
```

### 2. Run the Automated Setup Script
Run the automated script to install system dependencies (`ffmpeg`, `libopus`, `libffi`, etc.), create the Python virtual environment, install CPU-optimized PyTorch (saves ~2.5GB of RAM/disk), and set up your `.env` file:

```bash
bash setup_and_run.sh
```

---

## 🔄 Running 24/7 in the Background (Systemd Service)

To keep the bot running 24/7 on your Contabo server (even when you close your SSH terminal or reboot the VPS), turn it into a system service:

```bash
bash create_service.sh
```

### Systemd Management Commands:
- **Check Bot Status:** `sudo systemctl status summarizebot`
- **View Live Logs:** `sudo journalctl -u summarizebot -f`
- **Restart Bot:** `sudo systemctl restart summarizebot`
- **Stop Bot:** `sudo systemctl stop summarizebot`

---

## 🐳 Alternative: Running with Docker

If you prefer using Docker on your Contabo box:

1. Create your `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env and paste your DISCORD_TOKEN
   ```
2. Start the container in detached background mode:
   ```bash
   docker-compose up -d
   ```
3. View logs:
   ```bash
   docker logs summarizebot -f
   ```

---

## 📥 How to Update the Bot (Without Re-cloning)

To pull the latest code updates from GitHub without deleting your configuration:

```bash
# Force reset to latest remote version
git fetch --all
git reset --hard origin/main

# Restart the service (if using systemd)
sudo systemctl restart summarizebot

# OR restart setup_and_run script
bash setup_and_run.sh
```

---

## 📊 Checking Logs & Debugging

If the bot encounters an error or fails to join a channel:

- **If running via Systemd service:**
  ```bash
  sudo journalctl -u summarizebot -n 100 -f
  ```
- **If running manually in background with log saving:**
  ```bash
  python bot.py > bot.log 2>&1 &
  tail -f bot.log
  ```
- **If running via Docker:**
  ```bash
  docker logs summarizebot --tail 100 -f
  ```

---

## 🤖 Discord Slash Commands

- `/join`: Joins the voice channel you are currently in.
- `/record`: Starts recording the voice channel.
- `/stop`: Stops recording, processes audio, generates local transcript, and sends files to chat.
- `/leave`: Disconnects the bot from the voice channel.
