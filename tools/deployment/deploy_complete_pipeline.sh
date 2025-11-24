#!/bin/bash
# Complete KaizenLap ML Pipeline Deployment
# Deploys all 5 Cloud Run Jobs + Gemma Service
# For competition judges to reproduce

set -e

# Environment variables - set these to your GCP project values
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project)}"
# Region resolution order: CLOUD_RUN_REGION > GCP_REGION > gcloud config run/region > default
REGION="${CLOUD_RUN_REGION:-${GCP_REGION:-$(gcloud config get-value run/region)}}"
if [ -z "$REGION" ] || [ "$REGION" = "(unset)" ]; then
  REGION="europe-west1"
fi
GCS_BUCKET="${GCS_BUCKET:-${PROJECT_ID}-data}"
DOCKER_REPO="${DOCKER_REPO:-us-docker.pkg.dev/${PROJECT_ID}/ml-repo}"

echo "================================================================================"
echo "KAIZENLAP COMPLETE ML PIPELINE DEPLOYMENT"
echo "================================================================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Build ML Processor Image
echo "Step 1: Building ML processor Docker image..."
gcloud builds submit --config infrastructure/gcp/cloudbuild.yaml . \
  || { echo "Build failed"; exit 1; }

IMAGE="${DOCKER_REPO}/ml-processor:latest"

# Step 2: Create/Update Jobs
echo ""
echo "Step 2: Creating Cloud Run Jobs..."

# Job 1: Init & Compute
gcloud run jobs create init-and-compute \
  --image $IMAGE --region $REGION \
  --memory 16Gi --cpu 8 --max-retries 0 --task-timeout 20m \
  --set-env-vars="FIRESTORE_PROJECT_ID=$PROJECT_ID" \
  --args="tools/pipeline/run_init_and_compute.py,--mode,cloud" \
  2>/dev/null || gcloud run jobs update init-and-compute --image $IMAGE --region $REGION

# Jobs 2-4: Analysis Jobs
for job in section weather pattern; do
  gcloud run jobs create process-${job}-analysis \
    --image $IMAGE --region $REGION \
    --memory 16Gi --cpu 8 --max-retries 0 --task-timeout 20m \
    --set-env-vars="FIRESTORE_PROJECT_ID=$PROJECT_ID" \
    2>/dev/null || gcloud run jobs update process-${job}-analysis --image $IMAGE --region $REGION
done

# Step 3: Execute Pipeline
echo ""
echo "Step 3: Executing data pipeline..."

# Execute Job 1
echo "  Executing Job 1: Init & Compute..."
gcloud run jobs execute init-and-compute --region $REGION --wait

# Execute Jobs 2-4 for all races
echo "  Executing Jobs 2-4 for 14 races..."
for race_id in {1..14}; do
  case $race_id in
    1|2) track="barber";;
    3|4) track="cota";;
    5|6) track="indianapolis";;
    7|8) track="road-america";;
    9|10) track="sebring";;
    11|12) track="sonoma";;
    13|14) track="vir";;
  esac
  
  echo "    Processing Race $race_id ($track)..."
  gcloud run jobs execute process-section-analysis --args="$race_id,$track" --region $REGION --wait --quiet
  gcloud run jobs execute process-weather-analysis --args="$race_id" --region $REGION --wait --quiet
  gcloud run jobs execute process-pattern-analysis --args="$race_id" --region $REGION --wait --quiet
done

# Step 4: Deploy Gemma 3 Service
echo ""
echo "Step 4: Deploying Gemma 3 service..."
gcloud run deploy gemma3-inference \
  --image us-docker.pkg.dev/cloudrun/container/gemma/gemma3-4b:latest \
  --gpu 1 --gpu-type nvidia-l4 \
  --region $REGION --memory 16Gi --cpu 8 \
  --max-instances 1 --min-instances 0 \
  --timeout 300 \
  --set-env-vars="OLLAMA_NUM_PARALLEL=1" \
  --concurrency 1 \
  --allow-unauthenticated

GEMMA_URL=$(gcloud run services describe gemma3-inference --region=$REGION --format='value(status.url)')

# Step 5: Create & Execute Coaching Job
echo ""
echo "Step 5: Creating coaching generation job..."

gcloud run jobs create generate-coaching-insights \
  --image $IMAGE --region $REGION \
  --memory 8Gi --cpu 4 --max-retries 0 --task-timeout 120m \
  --set-env-vars="FIRESTORE_PROJECT_ID=$PROJECT_ID,GEMMA_ENDPOINT=$GEMMA_URL" \
  --args="generate_coaching_insights.py" \
  2>/dev/null || gcloud run jobs update generate-coaching-insights \
  --image $IMAGE --region $REGION \
  --set-env-vars="GEMMA_ENDPOINT=$GEMMA_URL"

echo "  Executing Job 5: Coaching generation (this takes ~90 minutes)..."
gcloud run jobs execute generate-coaching-insights --region $REGION --wait

# Step 6: Clean up (stop Gemma to avoid billing)
echo ""
echo "Step 6: Stopping Gemma service (data generation complete)..."
gcloud run services delete gemma3-inference --region $REGION --quiet

echo ""
echo "================================================================================"
echo "PIPELINE COMPLETE"
echo "================================================================================"
echo ""
echo "Firestore collections populated:"
echo "  - tracks: 7"
echo "  - races: 14"
echo "  - best_case_composites: 62"
echo "  - ml_section_recommendations: ~21,000"
echo "  - ml_weather_recommendations: 14"
echo "  - ml_pattern_recommendations: ~357"
echo "  - coaching_insights: ~349 (97%+ success rate)"
echo ""
echo "Total documents: ~21,700"
echo "Total cost: ~$12"
echo "Total time: ~3 hours"
echo ""
echo "Next: Deploy API and Frontend services"
