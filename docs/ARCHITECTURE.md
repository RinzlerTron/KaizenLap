# Technical Architecture

**System design and infrastructure for KaizenLap.**

---

## System Overview

```
Raw Telemetry (CSV) → Analytics Pipeline → AI Synthesis → Firestore → API → React UI
     2GB                4 parallel jobs       Gemma 3      21K docs   FastAPI   <100ms
```

**Design Goal:** Process the complete TRD dataset to generate coaching insights that respond instantly during judging.

---

## Data Pipeline

### Stage 1: Raw Data (Google Cloud Storage)

**144 CSV files** across 7 tracks and 14 races:
- Lap times (best lap, position changes)
- Section times (3 sections per track, except Road America Race 1)
- Weather conditions (temperature, humidity, wind, rain probability)
- Field positions (running order throughout race)

**500+ vehicles** tracked across full race distance.

### Stage 2: Analytics Processing (Cloud Run Jobs)

Four analytics engines process the telemetry in parallel to build the statistical foundation:

**Job 1: Best-Case Composite** (62 documents)  
Combines fastest section times across all drivers to create theoretical "perfect lap" for each race.

**Job 2: Section Analysis** (20,907 documents)  
Compares every driver's section times against best-case composite. Identifies where time is lost and calculates lap-to-lap variability.

**Job 3: Weather Correlation** (14 documents)  
Multi-variate analysis correlating temperature, humidity, wind, rain with lap time performance. Separates driver improvement from environmental changes.

**Job 4: Pattern Detection** (357 documents)  
Lap-to-lap consistency scoring, improvement/degradation trend analysis, standard deviation modeling.

These four jobs run in parallel since they're independent analyses of the same source data.

**Processing time:** ~35 minutes for all four jobs combined

### Stage 3: AI Synthesis (Gemma 3)

**After** the statistical engines complete, Gemma 3 reads their outputs to generate coaching insights.

**Why sequential:** Gemma 3 needs results from all four analytics engines to synthesize comprehensive recommendations. It converts statistical patterns into race engineer language.

**How it works:**  
Gemma 3 receives structured input from all four engines for each driver-lap combination. It's prompted to separate observable facts from theoretical explanations and provide specific, testable actions.

See [ML-APPROACH.md](ML-APPROACH.md) for detailed explanation of the AI coaching synthesis methodology.

**Processing time:** ~10 minutes  
**Output:** 357 coaching documents

### Stage 4: Storage (Firestore)

**21,718 documents** across 7 collections:

| Collection | Count | Purpose |
|------------|-------|---------|
| tracks | 7 | Track metadata + map configurations |
| races | 14 | Race events |
| best_case_composites | 62 | Theoretical perfect laps |
| ml_section_recommendations | 20,907 | Corner-specific coaching |
| ml_weather_recommendations | 14 | Condition analysis |
| ml_pattern_recommendations | 357 | Consistency scoring |
| coaching_insights | 357 | Gemma 3 strategic advice |

**Why Firestore:**
- NoSQL handles varying data structures (Road America's missing sections, races with different field counts)
- Built-in indexing enables sub-100ms queries without manual optimization
- Serverless—no database management overhead
- Flexible schema accommodates real-world data anomalies

**Indexing strategy:**
- Compound indexes on driver_id + race_id + lap_number for fast recommendation lookups
- Single-field indexes on track_id for race listing
- Query optimization tested to ensure <100ms p95 latency during judge evaluation

### Stage 5: API Layer (FastAPI)

**Endpoints:**
```
GET  /tracks              # List all tracks with metadata
GET  /races/{track_id}    # Races for specific track
GET  /recommendations     # Coaching insights (filtered by driver/lap/race)
GET  /health              # Service status
```

**Design choices:**
- Async connections for non-blocking I/O
- Query parameter validation via Pydantic models
- CORS handled server-side (frontend and backend same origin)
- Error handling with structured responses

**Response times:**
- Track list: 45ms
- Race data: 68ms
- Recommendations (single lap): 92ms
- Bulk recommendations (full race): 3.2s

### Stage 6: Frontend (React)

**Key components:**
- **Interactive SVG track maps** with section-level performance overlay
- **Draggable panels** that keep coaching visible while exploring data
- **4 analysis modes** (sections, weather, patterns, AI) via toggle interface
- **No authentication** for judge-friendly instant access

**Implementation details:**
- Material-UI component library for consistent design
- Code splitting for faster initial load
- React 18 concurrent rendering for smooth interactions
- SVG rendering for scalable track maps (not pixelated images)

---

## Deployment Architecture

**Single Service Model:**

KaizenLap deploys as one Cloud Run service containing both FastAPI backend and React frontend static files. This bundled approach eliminates CORS complexity, simplifies deployment, and provides judges a single URL to access the complete application.

**Build process:**
1. React frontend builds to static files
2. FastAPI bundles static files into container
3. Single Docker image deployed to Cloud Run
4. FastAPI serves both API endpoints and frontend assets

**Why bundled:**
- ❌ Separate = 2× deployment complexity, CORS configuration, dual monitoring
- ✅ Bundled = single URL, no CORS, one deploy command, same-origin simplicity

---

## Technology Choices Explained

### Cloud Run (Serverless Containers)
**Why:** Scales from zero to handle judge evaluation traffic, then back to zero. Zero-downtime deploys via rolling updates. No infrastructure management—just deploy containers.

### Gemma 3 (Open-Source LLM on Vertex AI)
**Why:** Self-hosted eliminates API rate limits and per-token costs. 4B parameters sufficient for structured coaching synthesis. Full control over prompt engineering and model behavior.

**Alternative considered:** GPT-4 API would cost significantly more for 21K recommendations and introduce rate limit dependencies during heavy evaluation.

### Firestore (NoSQL Database)
**Why:** Flexible schema handles data variance (Road America missing sections, varying race structures). NoSQL scales horizontally without sharding complexity. Built-in indexing with minimal configuration.

**Alternative considered:** Cloud SQL would require rigid schema that fails on incomplete data and manual index optimization.

### Bundled Frontend + Backend
**Why:** Eliminates CORS preflight requests (faster). Single deployment (simpler CI/CD). Same-origin authentication and session handling. One service URL for judges.

**Alternative considered:** Separate services add deployment overhead and CORS complexity without meaningful benefits for this use case.

### Pre-Computed Insights
**Why:** Demo responsiveness (judges won't wait for AI processing). Cost predictability (process once, serve unlimited times). Realistic for production (nightly batch jobs are standard in motorsport).

**Alternative considered:** On-demand computation would introduce 30-60s latency per request and unpredictable compute costs during evaluation.

---

## Data Quality & Caveats

The TRD dataset represents real-world racing telemetry with real-world data characteristics:

**Identified caveats:**
- **Road America Race 1:** Missing Section 2 timing data (sensor coverage gap)
- **Race 13:** Missing weather data fields
- **Varying data structures:** Some races have additional telemetry fields not present in others
- **Track map imagery:** Visual track representations don't always align perfectly with CSV section boundaries

**Design decision:**
The system focuses on **Race 1 and Race 2 from each track** because these races consistently contain the most complete data structure. This provides the strongest foundation for comparative analysis and coaching quality evaluation.

**Handling approach:**
Rather than rigid schemas that fail on incomplete data, the system detects data structure variance and adapts:
- Missing sections → adjust track configuration and visualization
- Missing weather → skip weather correlation for that race
- Extra fields → ignore non-essential columns
- Graceful degradation ensures judges see clean analytics rather than error messages

**Outcome:**
Judges evaluate coaching quality based on clean analytics rather than watching the system struggle with data gaps. This demonstrates production-grade fault tolerance—the kind required when working with live racing telemetry where sensor failures are operational realities.

**Future refinement:**
Analysis accuracy and coverage could be further enhanced with improved data quality standards: consistent section boundary definitions, complete weather station coverage, and standardized telemetry schemas across all races.

---

## Performance Metrics

**Query Response Times:**
- Track list: 45ms
- Race data: 68ms
- Recommendations (single lap): 92ms
- Bulk recommendations (full race): 3.2s

**Processing Times:**
- Analytics pipeline (4 parallel jobs): ~35 minutes
- Gemma 3 synthesis (sequential): ~10 minutes
- Firestore batch write: ~12 minutes
- **Total end-to-end:** ~60 minutes

**Concurrency:**
- 80 requests per Cloud Run instance
- 1-2 instances deployed (cost control + availability)
- Sub-100ms p95 latency maintained under load

---

## Scaling Considerations

**Current scale:**
- 14 races, 500 vehicles, 21K recommendations
- Sub-100ms API response
- 2-instance maximum

**Future scale (if productionized):**

**Real-time telemetry processing:**
- Replace CSV upload with streaming ingestion from track systems
- Cloud Run Jobs → Cloud Run Services (persistent connections)
- Firestore writes become streaming updates every 2-5 seconds
- Frontend polls or uses WebSockets for live recommendation updates
- Race engineers get split-second strategic intelligence during live sessions

**Multi-season analysis:**
- Firestore subcollections organize by season
- Historical queries: "How does this driver's COTA performance compare to last season?"
- Aggregate statistics and trend analysis across years
- Driver development tracking over time

**Live race strategy:**
- Pit window optimization based on tire degradation models
- Fuel strategy recommendations (pace × remaining laps × safety car probability)
- Competitor pace tracking and position predictions
- Real-time what-if scenarios ("If we pit now vs. 2 laps from now...")

**Architecture supports all of this** without major rewrites. Serverless foundation scales horizontally.

---

## Security Model

**Service Account Authentication:**
- Cloud Run → Firestore: Automatic via IAM permissions
- Cloud Run → GCS: Automatic (no keys in code)
- Environment variables for configuration (no hardcoded values)

**Public API (by design):**
- No authentication required (judges need instant access)
- Read-only endpoints (no write/delete operations exposed)
- Rate limiting via Cloud Run (80 concurrent requests/instance)

**Resource Protection:**
- `max-instances=2` caps worst-case resource usage
- `timeout=60s` kills long-running requests
- Budget alerts for monitoring spend

---

## Configuration Management

All configuration via environment variables (no hardcoded values):

| Variable | Purpose |
|----------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID |
| `GCS_BUCKET_NAME` | Storage bucket name |
| `USE_LOCAL_FILES` | `false` for cloud, `true` for local dev |
| `FIRESTORE_PROJECT_ID` | Firestore project (can differ from main project) |

---

See [ML-APPROACH.md](ML-APPROACH.md) for algorithm details and [DEPLOYMENT.md](DEPLOYMENT.md) for reproduction steps.
