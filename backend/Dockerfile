FROM python:3.11-slim

WORKDIR /app

# System deps: weasyprint (PDF) + ffmpeg (voice pipeline) + Playwright runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info fonts-liberation \
    ffmpeg libsndfile1 curl \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 libwayland-client0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Playwright Chromium headless shell (para web_automation skill)
ENV PLAYWRIGHT_BROWSERS_PATH=/pw-browsers
RUN python -m playwright install chromium chromium-headless-shell --with-deps || \
    python -m playwright install chromium chromium-headless-shell

COPY . .

# Voice models persist outside container
VOLUME ["/app/voice_models"]

ENV VOICE_MODELS_DIR=/app/voice_models \
    OMP_NUM_THREADS=8 \
    CUDA_VISIBLE_DEVICES=-1

EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
