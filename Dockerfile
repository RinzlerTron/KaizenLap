# Optimized Dockerfile with Build Caching

# Stage 1: Build React frontend
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

# Copy package files first (leverage Docker layer caching)
COPY frontend/package*.json ./

# Install dependencies (cached if package.json hasn't changed)
RUN npm ci --prefer-offline --no-audit

# Copy source and build
COPY frontend/ ./

# Set environment variable for production build
ENV REACT_APP_API_URL=""

RUN npm run build

# Stage 2: Python backend with frontend build
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (cached layer)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (leverage caching)
COPY backend/requirements-prod.txt ./requirements.txt

# Install Python dependencies (cached if requirements haven't changed)
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/app ./app

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/build ./frontend/build

# Cloud Run uses PORT environment variable
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Run FastAPI with uvicorn
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2

