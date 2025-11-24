# System Architecture

KaizenLap transforms racing telemetry through a multi-stage cloud pipeline into actionable driver coaching.

---

## Overview

**Data Layer:** Google Cloud Storage (CSV files) + Firestore (processed insights)  
**Processing:** 5 Cloud Run jobs for ML analysis  
**Serving:** Single Cloud Run service (FastAPI backend + React frontend)

---

## Data Flow

```
┌──────────────────────────────────────────────┐
│ Stage 1: Raw Telemetry (GCS)                 │
│  • 144 CSV files across 7 tracks, 14 races   │
│  • Lap times, sections, weather, positions   │
└────────────────┬─────────────────────────────┘
                 ↓
┌──────────────────────────────────────────────┐
│ Stage 2: Batch Analytics (Cloud Run Jobs)    │
│  Job 1: Best-case composite calculation      │
│  Job 2: Section gap analysis                 │
│  Job 3: Weather correlation                  │
│  Job 4: Consistency pattern detection        │
│  Job 5: Gemma 3 AI coaching synthesis        │
└────────────────┬─────────────────────────────┘
                 ↓
┌──────────────────────────────────────────────┐
│ Stage 3: Storage (Firestore)                 │
│  • 21,718 structured coaching documents      │
│  • 7 collections indexed for sub-100ms query │
└────────────────┬─────────────────────────────┘
                 ↓
┌──────────────────────────────────────────────┐
│ Stage 4: API Layer (FastAPI)                 │
│  • RESTful endpoints                         │
│  • Async database connections                │
│  • Error handling & validation               │
└────────────────┬─────────────────────────────┘
                 ↓
┌──────────────────────────────────────────────┐
│ Stage 5: Presentation (React)                │
│  • Interactive track maps (SVG rendering)    │
│  • Real-time section comparison              │
│  • 4 AI analysis types (toggle interface)    │
└──────────────────────────────────────────────┘
```

---

## Firestore Collections

| Collection | Documents | Purpose |
|------------|-----------|---------|
| `tracks` | 7 | Track metadata and configurations |
| `races` | 14 | Race events (2 per track) |
| `best_case_composites` | 62 | Optimal section time combinations |
| `ml_section_recommendations` | 20,907 | Corner-specific coaching |
| `ml_weather_recommendations` | 14 | Condition-performance correlation |
| `ml_pattern_recommendations` | 357 | Driver consistency analysis |
| `coaching_insights` | 357 | Gemma 3 AI strategic insights |
| **Total** | **21,718** | **Complete coaching dataset** |

---

## Technology Stack

### Backend
- **Framework:** FastAPI (async Python web framework)
- **Database:** Google Firestore (NoSQL, serverless)
- **Storage:** Google Cloud Storage (object storage)
- **Auth:** Service account (automatic via Cloud Run)

### Frontend
- **Framework:** React 18
- **UI Library:** Material-UI v5
- **Build:** Create React App
- **Deployment:** Static files served by FastAPI

### ML Pipeline
- **Model:** Gemma 3 (4B parameters, open-source)
- **Platform:** Vertex AI with L4 GPU
- **Jobs:** Cloud Run batch jobs (scale-to-zero)
- **Languages:** Python (pandas, scikit-learn)

### Infrastructure
- **Compute:** Cloud Run (serverless containers)
- **Build:** Cloud Build (automatic Docker builds)
- **Networking:** HTTPS with automatic SSL
- **Region:** Configurable (default: europe-west1)

---

## Deployment Model

**Bundled Service** (Single Cloud Run deployment):
- FastAPI serves both API endpoints and React static files
- No CORS complexity (same origin)
- Single build and deployment process
- Simplified networking and authentication

**Alternative Considered:** Separate frontend/backend services
- **Rejected:** 2x deployment overhead, CORS configuration, dual monitoring

---

## Data Processing Architecture

### Best-Case Composite
Combines fastest section times across all drivers to create theoretical perfect lap.

**Algorithm:**
```python
for section in track.sections:
    composite[section] = min(all_drivers[section].times)
```

**Use case:** Shows driver's gap to absolute best possible performance

### Section Analysis
Compares each driver's section time to composite, identifies specific corners losing time.

**Output:** "You were +0.5s slower in Section 2 (Turn 4-6)"

### Weather Correlation
Multi-variate analysis of weather conditions (temp, humidity, wind) against lap times.

**Technique:** Pearson correlation with significance testing

### Pattern Detection
Time-series analysis of lap-to-lap performance for consistency scoring.

**Metrics:**
- Standard deviation of lap times
- Improvement/degradation trend
- Consistency score (0-100)

### AI Coaching (Gemma 3)
LLM analyzes lap-by-lap data to separate facts from theories, provides evidence-based recommendations.

**Prompt engineering:** "Identify observable patterns (facts), hypothesize causes (theories), suggest specific technique changes (recommendations)"

---

## Scalability Design

### Current Scale
- 14 races, 500+ vehicles
- 21,718 pre-computed recommendations
- <100ms API response (Firestore indexing)
- 2-instance max (cost cap)

### Future Scale (if productionized)
- **Real-time processing:** Streaming telemetry ingestion
- **Historical analysis:** Multi-season comparisons
- **Live predictions:** In-race strategy recommendations
- **Horizontal scaling:** Cloud Run auto-scales to demand

### Design Decisions for Scale
- **Batch processing:** Run ML once, serve many times (vs. compute-per-request)
- **NoSQL:** Firestore handles flexible schema (varying section counts per track)
- **Stateless:** Cloud Run enables zero-downtime rolling updates
- **Caching:** Pre-computed recommendations avoid expensive re-calculation

---

## Data Quality Handling

**Known Issues:**
- Road America Race 1: Missing Section 2 timing data (sensor malfunction)

**Mitigation:**
- Application detects and displays 2-section layout for affected race
- Graceful UI degradation (no errors shown to user)
- Best-case composite correctly computed with available sections

**Validation Pipeline:**
- CSV schema validation on upload
- Missing column detection and logging
- Section count verification per track
- Automatic fallback for incomplete data

---

## Security Architecture

### Zero-Credential Design
- All API keys via environment variables (never in code)
- Service account authentication (automatic on Cloud Run)
- No hardcoded project IDs or bucket names
- Frontend never accesses credentials

### Network Boundaries
```
┌──────────────────┐
│ Browser (Public) │ ← HTTPS only
└────────┬─────────┘
         ↓
┌────────────────────────────┐
│ Cloud Run (Service)        │ ← Service account auth
│  - Public API endpoints     │
│  - Read-only operations     │
└────────┬───────────────────┘
         ↓
┌────────────────────────────┐
│ Firestore (Private)        │ ← Server-side only
│ GCS (Private)              │ ← IAM permissions
└────────────────────────────┘
```

### Attack Surface Mitigation
- **max-instances:** Caps worst-case costs
- **timeout:** 60s kills runaway requests
- **concurrency:** 80 connections per instance
- **read-only:** No DELETE/PUT endpoints exposed

---

## Monitoring & Observability

### Health Checks
```bash
curl https://service-url/health
# {"status":"healthy","version":"1.0"}
```

### Logging
- **Platform:** Cloud Logging (automatic from Cloud Run)
- **Levels:** INFO, WARNING, ERROR structured logs
- **Retention:** 30 days default

### Metrics
- Request count, latency, error rate (automatic)
- Database query performance (Firestore metrics)
- Cost tracking (GCP billing dashboard)

---

## Deployment Pipeline

```
Local Code Change
    ↓
Git Push
    ↓
Cloud Build Trigger (automatic)
    ↓
Multi-stage Docker Build
    │
    ├── Stage 1: React frontend build (npm run build)
    └── Stage 2: FastAPI backend + frontend bundle
    ↓
Container Registry
    ↓
Cloud Run Deploy (rolling update)
    ↓
Health Check Validation
    ↓
Live Traffic (zero downtime)
```

**Build time:** 4-8 minutes  
**Rollback:** Instant (Cloud Run revision history)

---

## Cost Optimization

**Techniques:**
- **Batch ML:** Process once, serve many (vs. real-time compute)
- **Serverless:** Cloud Run scales to zero between requests
- **Open-source:** Gemma 3 (no per-token API fees)
- **Free tiers:** Firestore, Cloud Run within limits

---

## References

- **Deployment:** See `docs/DEPLOYMENT.md`
- **Operations:** See `docs/OPERATIONS.md`
- **ML Approach:** See `docs/ML-APPROACH.md`
