# Stage 1: Build React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Production image
FROM python:3.12-slim

# Firefox/X11/KasmVNC runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdbus-1-3 libdrm2 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libx11-xcb1 libfontconfig1 libx11-6 \
    libxcb1 libxext6 libxshmfence1 \
    libglib2.0-0 libgtk-3-0 libpangocairo-1.0-0 libcairo-gobject2 \
    libgdk-pixbuf-2.0-0 libxss1 libxtst6 fonts-liberation \
    libgl1-mesa-dri libegl-mesa0 \
    procps wget ca-certificates xclip git \
    && rm -rf /var/lib/apt/lists/*

# Install KasmVNC. invisible_playwright currently ships Linux x86_64 Firefox.
ARG TARGETARCH=amd64
RUN test "$TARGETARCH" = "amd64"
RUN wget -q https://github.com/kasmtech/KasmVNC/releases/download/v1.3.3/kasmvncserver_bookworm_1.3.3_${TARGETARCH}.deb \
    && apt-get update && apt-get install -y -f ./kasmvncserver_bookworm_1.3.3_${TARGETARCH}.deb \
    && rm kasmvncserver_bookworm_1.3.3_${TARGETARCH}.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV MOZ_ENABLE_WAYLAND=0 GDK_BACKEND=x11

# Python deps
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt \
    && python -m playwright install-deps firefox \
    && python -m invisible_playwright fetch \
    && rm -rf /var/lib/apt/lists/*

# Backend code
COPY backend/ /app/backend/

# Frontend build from stage 1
COPY --from=frontend-builder /build/dist /app/frontend/dist

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/status')" || exit 1

VOLUME /data

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
