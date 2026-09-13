FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install FFmpeg and basic utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fontconfig \
    curl \
    wget \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download Khmer Font for subtitles
RUN mkdir -p /usr/share/fonts/truetype/khmer && \
    wget -qO /usr/share/fonts/truetype/khmer/Battambang-Regular.ttf https://raw.githubusercontent.com/google/fonts/main/ofl/battambang/Battambang-Regular.ttf || true && \
    fc-cache -f -v || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads temp_dubbing_files Downloaded_Videos Exported_Videos

EXPOSE 8000

CMD ["python", "main.py"]

