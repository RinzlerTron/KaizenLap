# Deployment Guide

Simplified deployment for Google Cloud Platform. Designed for reproducibility by judges and technical reviewers.

---

## Prerequisites

- Google Cloud Project with billing enabled
- `gcloud` CLI installed and authenticated
- Dataset from Hack the Track 2025

---

## Architecture

**Single Cloud Run Service** - Bundled FastAPI backend + React frontend  
**Data Layer** - Firestore (21K documents) + Cloud Storage (2GB telemetry)  
**ML Pipeline** - 5 Cloud Run jobs for batch processing

---

## Quick Deploy (3 Steps)

### Step 1: Configure Project

```bash
# Set your GCP project ID
export GCP_PROJECT_ID=your-project-id
export GCS_BUCKET=${GCP_PROJECT_ID}-data
export REGION=europe-west1

# Authenticate
gcloud auth login
gcloud config set project ${GCP_PROJECT_ID}
```

### Step 2: Upload Data

```bash
# Create storage bucket
gcloud storage buckets create gs://${GCS_BUCKET} --location=${REGION}

# Upload telemetry data
gcloud storage cp -r local/data/cloud_upload/primary gs://${GCS_BUCKET}/
gcloud storage cp -r local/data/cloud_upload/processed gs://${GCS_BUCKET}/
```

**What's uploaded:**
- 7 tracks × 2 races = 14 race events
- 144 CSV files with lap/section timing
- 7 JSON track map configurations

**Data Notes:**
- Road America Race 1 missing S2 data (sensor issue)
- All other 13 races have complete 3-section data
- ~2GB total data size

### Step 3: Deploy Application

Using PowerShell (Windows):
```powershell
.\deploy-cloudrun.ps1 -ProjectId your-project-id
```

Or using gcloud directly:
```bash
gcloud run deploy kaizenlap \
  --source . \
  --region ${REGION} \
  --platform managed \
  --port 8080 \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 2 \
  --cpu 2 \
  --memory 2Gi \
  --set-env-vars GOOGLE_CLOUD_PROJECT=${GCP_PROJECT_ID},GCS_BUCKET_NAME=${GCS_BUCKET},USE_LOCAL_FILES=false
```

**Build time:** 4-8 minutes (automatic via Cloud Build)

---

## Optional: ML Pipeline

The deployment includes basic analytics. For full AI coaching insights (Gemma 3), run:

```bash
# Initialize database
pip install -r tools/pipeline/requirements.txt
export FIRESTORE_PROJECT_ID=${GCP_PROJECT_ID}
python tools/deployment/init_firestore_complete.py

# Run ML pipeline (processes all 14 races)
./tools/deployment/deploy_complete_pipeline.sh
```

**Processing time:** ~45 minutes  
**Output:** 21,718 coaching recommendations

---

## Verification

```bash
# Get service URL
gcloud run services describe kaizenlap --region=${REGION} --format="value(status.url)"

# Test health endpoint
curl $(gcloud run services describe kaizenlap --region=${REGION} --format="value(status.url)")/health

# Expected: {"status":"healthy","version":"1.0"}
```

---

## Configuration

All configuration via environment variables (no hardcoded values):

| Variable | Purpose |
|----------|---------|
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID |
| `GCS_BUCKET_NAME` | Data storage bucket |
| `USE_LOCAL_FILES` | false (uses cloud storage) |

---

## Project Structure

```
├── backend/              # FastAPI application
│   ├── app/api/         # REST endpoints
│   └── requirements-prod.txt
├── frontend/            # React application
│   └── src/components/  # UI components
├── tools/
│   ├── pipeline/        # ML analysis jobs
│   └── deployment/      # Initialization scripts
└── Dockerfile           # Multi-stage build
```

---

## Data Pipeline Stages

**Stage 1: Raw Telemetry** (CSV files)
- Lap times, section times, weather conditions
- 500+ vehicles across 14 races

**Stage 2: Analytics** (Cloud Run jobs)
- Best-case composite calculation (fastest section combination)
- Section analysis (gap identification per corner)
- Weather correlation (condition-performance analysis)
- Pattern detection (consistency and trends)

**Stage 3: AI Enhancement** (Gemma 3)
- Lap-by-lap pattern recognition
- Root cause diagnosis
- Evidence-based recommendations

**Stage 4: Storage** (Firestore)
- 21,718 structured coaching documents
- Indexed for sub-100ms API response

---

## Technology Choices

**Gemma 3 on Vertex AI** - Open-source LLM for cost-effective coaching insights at scale. Chosen over commercial LLM APIs so we can process 21K+ recommendations within the competition budget.

**Cloud Run Jobs** - Batch processing for ML pipeline. Scales to zero between runs, optimizing compute costs during data processing stages.

**Firestore** - NoSQL for flexible schema. Accommodates varying race data structures (Road America S2 caveat) without rigid table constraints.

---

## Troubleshooting

**Build fails:**
```bash
# Check Docker context
ls Dockerfile

# Verify gcloud authentication
gcloud auth list
```

**Service returns 500:**
```bash
# Check logs
gcloud run services logs read kaizenlap --region=${REGION} --limit=50
```

**Data missing:**
```bash
# Verify bucket contents
gcloud storage ls gs://${GCS_BUCKET}/primary/extracted/
```

---

## Cleanup

After evaluation:
```bash
# Stop service (stops charges)
gcloud run services delete kaizenlap --region=${REGION}

# Optional: Remove data
gcloud storage rm -r gs://${GCS_BUCKET}
```

---

**Deployment Time:** 15-60 minutes (depending on ML pipeline)  
**Region:** Configurable (default: europe-west1)  

