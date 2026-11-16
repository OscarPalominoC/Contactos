# Multi-stage Dockerfile para Check Contactos
# Permite construir tanto el backend como el frontend desde la raíz del proyecto.

# -------------------------------------------------------------
# Stage 1: Build de la aplicación frontend (React + Vite + TS)
# -------------------------------------------------------------
FROM node:22-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# -------------------------------------------------------------
# Stage: Frontend servidor Nginx (Target: frontend)
# -------------------------------------------------------------
FROM nginx:1.27-alpine AS frontend
COPY --from=frontend-builder /app/dist /usr/share/nginx/html
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 5173
CMD ["nginx", "-g", "daemon off;"]

# -------------------------------------------------------------
# Stage: Backend Django DRF (Target: backend / Default)
# -------------------------------------------------------------
FROM python:3.13-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Instalar dependencias del sistema mínimas requeridas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    openssl \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Instalar requerimientos de Python
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copiar código del backend, scripts y utilidades
COPY backend/ /app/backend/
COPY scripts/ /app/scripts/
COPY docker/backend/entrypoint.sh /app/docker/backend/entrypoint.sh
RUN sed -i '1s/^\xef\xbb\xbf//' /app/docker/backend/entrypoint.sh && \
    sed -i 's/\r$//' /app/docker/backend/entrypoint.sh && \
    chmod +x /app/docker/backend/entrypoint.sh

# Crear directorios para estáticos, logs y llaves RSA
RUN mkdir -p /app/backend/staticfiles /app/backend/keys /app/logs

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/app/docker/backend/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

