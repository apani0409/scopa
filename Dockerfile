# ── Stage 1: Build SvelteKit frontend ────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./

# Copy card images into the SvelteKit static folder so they're bundled
COPY napolitane/ ./static/assets/napolitane/

RUN npm run build


# ── Stage 2: Python backend ───────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Game engine + app layer
COPY src/ ./src/

# Card images (FastAPI serves them as /assets/napolitane/ for standalone use)
COPY napolitane/ ./napolitane/

# SvelteKit static build (served by FastAPI's SPA catch-all)
COPY --from=frontend-builder /app/frontend/build ./frontend/build

EXPOSE 8000

# Render (and most cloud platforms) injects $PORT at runtime.
# Fall back to 8000 for local Docker runs.
CMD ["sh", "-c", "uvicorn src.multiplayer.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
