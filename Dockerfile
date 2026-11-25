# --- Stage 1 : Build statique Astro ---
FROM node:26-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/astro.config.mjs frontend/tsconfig.json ./
COPY frontend/public ./public
COPY frontend/src ./src
RUN npm run build

# --- Stage 2 : Image finale (Nginx + Python/FastAPI) ---
FROM python:3.14-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv export --no-hashes --no-emit-project --no-dev > requirements.txt \
 && uv pip install --system --no-cache -r requirements.txt

COPY backend/main.py backend/config.py ./
COPY backend/database ./database
COPY backend/schemas ./schemas

COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]