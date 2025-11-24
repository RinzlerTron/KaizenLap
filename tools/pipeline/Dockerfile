# Dockerfile for ML Analysis Cloud Run Jobs (CPU-only)

# Purpose:
#   Runs ML analysis jobs for KaizenLap: section analysis, weather analysis, pattern analysis.
#   Loads processed telemetry and race data from GCS/Firestore, performs analysis,
#   and saves recommendations back to Firestore.
#   Uses CPU-only processing (pandas/numpy/scikit-learn).
#
# Cloud Run Jobs: ml-section-analysis, ml-weather-analysis, ml-pattern-analysis
# Entrypoint: Set dynamically by Cloud Run job configuration
# GPU: None (CPU-only processing)
#
# Usage Examples:
#   gcloud run jobs execute ml-section-analysis --args "13,barber"
#   gcloud run jobs execute ml-weather-analysis --args "13,barber"
#   gcloud run jobs execute ml-pattern-analysis --args "13,barber"
#
# Output:
#   - Firestore: ml_section_recommendations, ml_weather_recommendations, ml_pattern_recommendations collections

# Base Image: Standard Python (no CUDA needed for CPU processing)
FROM python:3.11-slim

# Environment Variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONPATH=/app \
    USE_GPU="false"

# These will be set at runtime by Cloud Run
# GCP_PROJECT_ID - Your GCP project ID
# GCS_BUCKET - Your GCS bucket name  
# FIRESTORE_PROJECT_ID - Usually same as GCP_PROJECT_ID

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY tools/pipeline/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Install CPU-only data processing libraries (pandas, numpy, scikit-learn)
# These replace cuDF/cuPy/cuML when USE_GPU=false
RUN pip3 install --no-cache-dir \
    pandas \
    numpy \
    scikit-learn \
    gcsfs

# Copy backend code (needed for app.config, app.utils.gpu_utils, etc.)
COPY backend/ /app/backend/

# Copy deployment scripts (for init_firestore_complete.py)
COPY tools/deployment/ /app/tools/deployment/

# Copy pipeline processing scripts
COPY tools/pipeline/ /app/tools/pipeline/

# Track maps are in GCS, will be loaded at runtime
# Create directory structure for track maps (they'll be loaded from GCS or bundled separately)
RUN mkdir -p /app/local/data/cloud_upload/processed/track_maps

# Entry point: Run Python script directly (no CUDA setup needed)
# Note: This image is used for multiple ML analysis jobs - entrypoint set at runtime by Cloud Run
ENTRYPOINT ["python3"]

