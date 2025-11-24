# KaizenLap Cloud Run Deployment Script
# Deploys the bundled frontend + backend to Google Cloud Run

param(
    [string]$ProjectId = $env:GCP_PROJECT_ID,
    [string]$Region = "us-west2",
    [string]$ServiceName = "kaizenlap"
)

# Exit on error
$ErrorActionPreference = "Stop"

Write-Host "=============================================================================="
Write-Host "KAIZENLAP CLOUD RUN DEPLOYMENT"
Write-Host "=============================================================================="
Write-Host ""

# Check required parameters
if (-not $ProjectId) {
    Write-Host "ERROR: GCP_PROJECT_ID not set" -ForegroundColor Red
    Write-Host "Usage: .\deploy-cloudrun.ps1 -ProjectId your-project-id"
    Write-Host "Or set environment variable: `$env:GCP_PROJECT_ID='your-project-id'"
    exit 1
}

# Default to new us-west2 bucket name (can be overridden via env var)
$GcsBucket = if ($env:GCS_BUCKET_NAME) { $env:GCS_BUCKET_NAME } else { "$ProjectId-data" }

# Firestore database ID (defaults to US database)
$FirestoreDatabaseId = if ($env:FIRESTORE_DATABASE_ID) { $env:FIRESTORE_DATABASE_ID } else { "kaizenlap-us" }

Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Project ID:   $ProjectId"
Write-Host "  Region:       $Region"
Write-Host "  Service Name: $ServiceName"
Write-Host "  GCS Bucket:   $GcsBucket"
Write-Host "  Firestore DB: $FirestoreDatabaseId"
Write-Host ""

# Confirm deployment
$confirmation = Read-Host "Deploy to Cloud Run? (y/n)"
if ($confirmation -ne 'y') {
    Write-Host "Deployment cancelled."
    exit 0
}

Write-Host ""
Write-Host "Building and deploying to Cloud Run..." -ForegroundColor Yellow
Write-Host ""

# Deploy using gcloud run deploy with source
# This will build the Docker image and deploy it
gcloud run deploy $ServiceName `
    --source . `
    --project=$ProjectId `
    --region=$Region `
    --platform=managed `
    --port=8080 `
    --allow-unauthenticated `
    --min-instances=1 `
    --max-instances=2 `
    --cpu=2 `
    --memory=2Gi `
    --timeout=60s `
    --concurrency=80 `
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId,GCS_BUCKET_NAME=$GcsBucket,USE_LOCAL_FILES=false,FIRESTORE_DATABASE_ID=$FirestoreDatabaseId"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=============================================================================="
Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "=============================================================================="
Write-Host ""

# Get service URL
$serviceUrl = gcloud run services describe $ServiceName --project=$ProjectId --region=$Region --format="value(status.url)" 2>$null

if ($serviceUrl) {
    Write-Host "Your KaizenLap application is live:" -ForegroundColor Green
    Write-Host ""
    Write-Host "  URL: $serviceUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Test it:"
    Write-Host "  Health Check: $serviceUrl/health"
    Write-Host "  API:          $serviceUrl/api/tracks"
    Write-Host "  Frontend:     $serviceUrl"
}

Write-Host ""
Write-Host "=============================================================================="

