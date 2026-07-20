#!/bin/bash

# --- Color Definitions ---
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${CYAN}${BOLD}====================================================${NC}"
echo -e "${CYAN}${BOLD}    SummarizeBot macOS Auto-Setup & Runner Script   ${NC}"
echo -e "${CYAN}${BOLD}====================================================${NC}"

# 1. Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}⚠️  Homebrew not found. It is required to install FFmpeg.${NC}"
    echo -e "Installing Homebrew... (this may prompt for your macOS password)"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo -e "${GREEN}✓ Homebrew is installed.${NC}"
fi

# 2. Check and Install FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}Installing FFmpeg via Homebrew...${NC}"
    brew install ffmpeg
else
    echo -e "${GREEN}✓ FFmpeg is already installed.${NC}"
fi

# 3. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install it using: brew install python${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Python 3 is installed.${NC}"
fi

# 4. Create and Configure .env
APP_ID="1528738174665494590"
PUBLIC_KEY="699174d8807f9eb18524726987435a4f30da272a954e4985bd575997711fbe8a"
ENV_FILE=".env"

# Prompt for Bot Token if .env does not exist or lacks DISCORD_TOKEN
token_exists=false
if [ -f "$ENV_FILE" ]; then
    if grep -q "DISCORD_TOKEN=" "$ENV_FILE" && ! grep -q "DISCORD_TOKEN=your_discord_bot_token_here" "$ENV_FILE" && [ "$(grep "DISCORD_TOKEN=" "$ENV_FILE" | cut -d'=' -f2)" != "" ]; then
        token_exists=true
    fi
fi

if [ "$token_exists" = false ]; then
    echo -e "\n${YELLOW}🔑 A Discord Bot Token is required to run the bot.${NC}"
    echo -e "You can get it from the Discord Developer Portal: https://discord.com/developers/applications"
    read -p "Please paste your Discord Bot Token: " bot_token
    
    # Save configuration to .env
    cat <<EOT > "$ENV_FILE"
# Discord Configuration
DISCORD_TOKEN=$bot_token
DISCORD_APPLICATION_ID=$APP_ID
DISCORD_PUBLIC_KEY=$PUBLIC_KEY

# Local Whisper Configuration
# Options: tiny, base, small, medium, large
WHISPER_MODEL=base
EOT
    echo -e "${GREEN}✓ Generated .env configuration file.${NC}"
else
    echo -e "${GREEN}✓ Existing .env configuration loaded.${NC}"
fi

# 5. Build Virtual Environment and Install Requirements
echo -e "\n${CYAN}📦 Setting up Python virtual environment and dependencies...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. Print Bot Invite Link
echo -e "\n${GREEN}${BOLD}🎉 Bot Setup is Complete!${NC}"
echo -e "${CYAN}Use this link to invite your bot to your Discord server:${NC}"
echo -e "${YELLOW}${BOLD}https://discord.com/oauth2/authorize?client_id=${APP_ID}&permissions=3180544&scope=bot%20applications.commands${NC}"
echo -e "${CYAN}Make sure to enable 'Guild Members' and 'Message Content' Gateway Intents in the Developer Portal!${NC}\n"

# 7. Start the Bot
echo -e "${GREEN}🤖 Starting SummarizeBot... (Press Ctrl+C to stop)${NC}\n"
python bot.py
