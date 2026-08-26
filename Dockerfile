FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fontconfig fonts-khmeros fonts-sil-mondulkiri curl wget git && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /usr/share/fonts/truetype/khmer && wget -qO /usr/share/fonts/truetype/khmer/Battambang-Regular.ttf https://github.com/google/fonts/raw/main/ofl/battambang/Battambang-Regular.ttf || true && fc-cache -fv
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p uploads temp_dubbing_files Downloaded_Videos Exported_Videos
EXPOSE 8000
CMD ["python", "main.py"]
