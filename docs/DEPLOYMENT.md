# Deployment

Get KaizenLap running in 10 minutes.

---

## Quick Start

**Prerequisites:**
- Google Cloud account with billing enabled
- `gcloud` CLI ([install](https://cloud.google.com/sdk/docs/install))

**Deploy:**

```bash
# 1. Set project
export GCP_PROJECT_ID=your-project-id
gcloud config set project ${GCP_PROJECT_ID}

# 2. Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com

# 3. Create storage
gcloud storage buckets create gs://${GCP_PROJECT_ID}-data --location=us-west2

# 4. Upload telemetry data (if you have the dataset)
gcloud storage cp -r local/data/cloud_upload/primary gs://${GCP_PROJECT_ID}-data/
gcloud storage cp -r local/data/cloud_upload/processed gs://${GCP_PROJECT_ID}-data/

# 5. Deploy
gcloud run deploy kaizenlap \
  --source . \
  --region us-west2 \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 2 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=${GCP_PROJECT_ID},GCS_BUCKET_NAME=${GCP_PROJECT_ID}-data,USE_LOCAL_FILES=false
```

**Deploy time:** 5-8 minutes (Cloud Build handles container creation automatically)

---

## Verify

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe kaizenlap --region=us-west2 --format="value(status.url)")

# Test health endpoint
curl $SERVICE_URL/health

# Expected: {"status":"healthy","version":"1.0"}

# Open in browser
echo "Visit: $SERVICE_URL"
```

---

## Optional: Full ML Pipeline

The deployment includes pre-computed recommendations. To regenerate all AI coaching insights from scratch:

```bash
# Install dependencies
pip install -r tools/pipeline/requirements.txt

# Initialize Firestore
export FIRESTORE_PROJECT_ID=${GCP_PROJECT_ID}
python tools/deployment/init_firestore_complete.py

# Run analytics pipeline
chmod +x tools/deployment/deploy_complete_pipeline.sh
./tools/deployment/deploy_complete_pipeline.sh
```

**Processing time:** ~45 minutes (4 parallel jobs + Gemma 3 synthesis)  
**Output:** 21,718 coaching recommendations written to Firestore

---

## Data Structure

**Telemetry files** (144 CSVs from Hack the Track dataset):
```
gs://{bucket}/primary/extracted/
├── barber/
│   ├── race1/ (GP_Laps.csv, GP_Sections.csv, GP_Positions.csv, GP_Weather.csv)
│   └── race2/ (same structure)
├── cota/
├── indianapolis/
├── road-america/
├── sebring/
├── sonoma/
└── vir/
```

**Track map configs** (7 JSON files):
```
gs://{bucket}/processed/tracks/
├── barber.json
├── cota.json
├── indianapolis.json
├── road_america.json
├── sebring.json
├── sonoma.json
└── vir.json
```

---

## Configuration

All configuration via environment variables:

| Variable | Purpose |
|----------|---------|
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID |
| `GCS_BUCKET_NAME` | Storage bucket name |
| `USE_LOCAL_FILES` | `false` for cloud storage, `true` for local dev |

---

## Troubleshooting

**Build fails:**
```bash
# Verify Docker context
ls Dockerfile backend/ frontend/

# Check authentication
gcloud auth list
gcloud auth application-default login
```

**Service returns errors:**
```bash
# View recent logs
gcloud run services logs read kaizenlap --region=us-west2 --limit=50

# Check environment variables
gcloud run services describe kaizenlap --region=us-west2 \
  --format="value(spec.template.spec.containers[0].env)"
```

**Data not found:**
```bash
# Verify bucket contents
gcloud storage ls gs://${GCP_PROJECT_ID}-data/primary/extracted/

# Check service account permissions
gcloud projects get-iam-policy ${GCP_PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*kaizenlap*"
```

---

## Cleanup

After evaluation:
```bash
# Delete service
gcloud run services delete kaizenlap --region=us-west2

# Optional: Remove data
gcloud storage rm -r gs://${GCP_PROJECT_ID}-data

# Optional: Delete Firestore data
gcloud firestore databases delete --database="(default)"
```

---

## Windows Deploy

**PowerShell:**
```powershell
.\deploy-cloudrun.ps1 -ProjectId your-project-id
```

The script handles project configuration, API enablement, bucket creation, and service deployment automatically.

---

## What Gets Deployed

**Single Cloud Run service** containing:
- FastAPI backend (Python)
- React frontend (static files served by FastAPI)
- Automatic HTTPS with SSL
- Serverless scaling (1-2 instances)

**Infrastructure created:**
- Cloud Run service (serverless container)
- Cloud Storage bucket (telemetry CSVs)
- Firestore database (21K coaching documents)

---

## Production Considerations

If Toyota wants to productionize this:

**Phase 1: Pilot with teams**
- Add team-specific authentication
- Custom branding per team
- Private data isolation

**Phase 2: Real-time telemetry**
- Streaming ingestion from track systems
- WebSocket connections for live updates
- Race engineer dashboard with split-second recommendations

**Phase 3: Full series deployment**
- Multi-region deployment
- Horizontal scaling (10-100 instances)
- CDN for global sub-100ms latency

Current architecture supports all of this without major rewrites.

---

See [ARCHITECTURE.md](ARCHITECTURE.md) and [ML-APPROACH.md](ML-APPROACH.md) for technical details.
