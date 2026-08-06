#!/bin/bash

# --- Color Definitions ---
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${CYAN}${BOLD}====================================================${NC}"
echo -e "${CYAN}${BOLD}   SummarizeBot Systemd 24/7 Service Generator      ${NC}"
echo -e "${CYAN}${BOLD}====================================================${NC}"

# Get current directory and user
BOT_DIR=$(pwd)
CURRENT_USER=$(whoami)
SERVICE_NAME="summarizebot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [ ! -f "${BOT_DIR}/venv/bin/python" ]; then
    echo -e "${RED}❌ Error: Virtual environment not found in ${BOT_DIR}/venv.${NC}"
    echo -e "${YELLOW}Please run 'bash setup_and_run.sh' first to set up the bot environment.${NC}"
    exit 1
fi

if [ ! -f "${BOT_DIR}/.env" ]; then
    echo -e "${RED}❌ Error: .env file not found in ${BOT_DIR}.${NC}"
    echo -e "${YELLOW}Please run 'bash setup_and_run.sh' first to configure your bot token.${NC}"
    exit 1
fi

echo -e "\n${CYAN}⚙️ Creating systemd service file: ${SERVICE_FILE}...${NC}"

sudo bash -c "cat <<EOT > ${SERVICE_FILE}
[Unit]
Description=SummarizeBot Discord Voice Recorder & Transcriber
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${BOT_DIR}
ExecStart=${BOT_DIR}/venv/bin/python ${BOT_DIR}/bot.py
Restart=always
RestartSec=5
EnvironmentFile=${BOT_DIR}/.env

[Install]
WantedBy=multi-user.target
EOT"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error: Failed to create service file. Ensure you have sudo privileges.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Created service file successfully.${NC}"

echo -e "\n${CYAN}🔄 Reloading systemd daemon and enabling service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start ${SERVICE_NAME}

echo -e "\n${GREEN}${BOLD}🎉 SummarizeBot is now running 24/7 in the background!${NC}"
echo -e "\n${CYAN}Useful Management Commands:${NC}"
echo -e "  - ${YELLOW}Check Bot Status:${NC}   sudo systemctl status ${SERVICE_NAME}"
echo -e "  - ${YELLOW}View Live Logs:${NC}     sudo journalctl -u ${SERVICE_NAME} -f"
echo -e "  - ${YELLOW}Restart Bot:${NC}        sudo systemctl restart ${SERVICE_NAME}"
echo -e "  - ${YELLOW}Stop Bot:${NC}           sudo systemctl stop ${SERVICE_NAME}"
