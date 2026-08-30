FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libportaudio2 \
    portaudio19-dev \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libgl1 \
    pulseaudio-utils \
    alsa-utils \
    xdg-utils \
    x11-utils \
    scrot \
    git \
    python3-tk \
    python3-dev \
    libglib2.0-bin \
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

RUN echo "pcm.!default {\n  type plug\n  slave.pcm \"pulse\"\n}\nctl.!default {\n  type pulse\n}" > /etc/asound.conf

WORKDIR /app

RUN pip install --no-cache-dir \
    sounddevice \
    numpy \
    scipy \
    faster-whisper \
    requests \
    chromadb \
    ollama \
    pyautogui \
    pillow \
    PyQt6 \
    piper-tts

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
