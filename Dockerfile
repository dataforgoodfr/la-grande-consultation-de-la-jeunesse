# --- Stage 1 : Build statique Astro ---
FROM node:26-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2 : Image finale (Nginx + Python/FastAPI) ---
FROM python:3.14-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python / FastAPI depuis pyproject.toml + uv.lock
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv export --no-hashes --no-emit-project > requirements.txt \
 && uv pip install --system --no-cache -r requirements.txt
COPY backend/ ./

# Fichiers statiques Astro -> Nginx
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# Configuration Nginx
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

EXPOSE 8080

# Lance FastAPI en arrière-plan puis Nginx au premier plan
CMD ["sh", "-c", "uvicorn main:app --host 127.0.0.1 --port 8000 & exec nginx -g 'daemon off;'"]