import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Discord Bot Token configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Local Whisper model configuration
# Options: tiny, base, small, medium, large
# "base" is the recommended default for most laptops/CPUs
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

def validate_config():
    """
    Validates that the required environment variables are set.
    """
    if not DISCORD_TOKEN:
        print("⚠️  Warning: DISCORD_TOKEN is not set in the environment variables.")
        print("Please check your .env file or environment setup.")
        return False
    return True
