FROM python:3.11-slim

# Install system dependencies (ffmpeg, libopus, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus0 \
    libopus-dev \
    libffi-dev \
    libnacl-dev \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install setuptools and CPU-optimized PyTorch
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "setuptools<82.0.0" wheel && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt

# Copy application files
COPY . .

# Run the bot
CMD ["python", "bot.py"]
