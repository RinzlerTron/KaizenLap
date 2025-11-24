# Operations Overview

Enterprise-grade operational practices applied to hackathon project. Demonstrates full-lifecycle management from development through competition deployment.

---

## System Design Philosophy

**Principle:** Production-ready architecture that scales from prototype to competition evaluation, with cost optimization and reliability built-in from day one.

**Approach:** Multi-layered data pipeline with staged processing, automated deployment, and budget protection mechanisms.

---

## Data Pipeline Architecture

### Stage 1: Ingestion & Validation
- **Source:** 144 CSV files (Toyota GR Cup telemetry)
- **Storage:** Google Cloud Storage with versioning
- **Format:** Semicolon-delimited, UTF-8 encoded
- **Quality:** Automated validation identifies missing data (e.g., Road America Race 1 S2 sensor gap)

### Stage 2: Analytics Processing
- **Platform:** 5 Cloud Run jobs (horizontal scaling)
- **Processing:** Parallelized across tracks and races
- **Output:** 21,718 structured recommendations
- **Compute:** Auto-scales to zero between runs

**Job Breakdown:**
1. **Best-case composite** - Statistical aggregation across drivers
2. **Section analysis** - Delta calculations with significance testing
3. **Weather correlation** - Multi-variate condition analysis
4. **Pattern detection** - Time-series consistency scoring
5. **Coaching insights** - Gemma 3 LLM synthesis

### Stage 3: AI Enhancement
- **Model:** Gemma 3 (4B parameters, open-source)
- **Deployment:** Vertex AI with L4 GPU
- **Cost optimization:** Open-source model eliminates per-token API costs
- **Processing:** Lap-by-lap analysis for 357 driver-race combinations

**Why Gemma 3:**
- Zero API fees (vs. $0.03/1K tokens for commercial models)
- On-device inference for consistent latency
- Full control over model deployment and scaling

### Stage 4: Serving Layer
- **API:** FastAPI with async database connections
- **Cache:** Firestore's built-in indexing (<100ms queries)
- **Frontend:** React with code-splitting for optimal load times

---

## Cost Optimization Strategy

**Budget Constraint:** $240 for 3-week competition period

**Optimization Decisions:**

| Decision | Traditional Approach | Our Approach | Savings |
|----------|---------------------|--------------|---------|
| LLM | GPT-4 API ($0.03/1K tokens) | Gemma 3 on Vertex | ~$150 |
| Compute | Always-on VM ($50/month) | Cloud Run (scale-to-zero) | ~$35 |
| Database | Cloud SQL ($25/month) | Firestore free tier | ~$15 |
| **Total** | **~$200 saved** | **Final cost: ~$60** | **75% reduction** |

**Techniques Applied:**
- Batch processing for ML (run once, serve many times)
- Stateless architecture (Cloud Run auto-scaling)
- Strategic use of free tiers (Firestore, Cloud Run within limits)
- Open-source models (Gemma 3 vs. proprietary APIs)

---

## Reliability & Monitoring

### Service Configuration
```yaml
min_instances: 1      # Always warm for judge access
max_instances: 2      # Cost cap ($113 worst-case)
cpu: 2                # Fixed resources
memory: 2Gi           # Prevents OOM
timeout: 60s          # Kill runaway requests
concurrency: 80       # Per-instance connection limit
```

### Data Quality Handling
**Known Issues:**
- Road America Race 1: Missing S2 timing data (sensor malfunction)
- **Mitigation:** Application detects and displays 2-section layout for this race
- **Impact:** 1 of 14 races affected; transparent to user

**Validation Pipeline:**
- CSV schema validation on upload
- Missing column detection
- Section count verification per track
- Graceful degradation for incomplete data

### Error Handling
- **API:** Structured error responses with actionable messages
- **Frontend:** Fallback UI states for missing data
- **Logging:** Cloud Run automatic log aggregation
- **Monitoring:** Health check endpoint (`/health`)

---

## Security Posture

### Zero-Credential Exposure
- All API keys via environment variables
- No hardcoded project IDs or bucket names
- Service account authentication (no key files)
- Frontend never touches credentials

### Network Security
- **GCS bucket:** Private (service account access only)
- **Firestore:** Server-side only rules
- **API:** Read-only endpoints (no DELETE/PUT)
- **Auth:** Public access by design (judge-friendly)

### Attack Surface Mitigation
- **DDOS protection:** max-instances cap limits blast radius
- **Rate limiting:** 80 concurrent requests per instance
- **Timeout:** 60s prevents resource exhaustion
- **Monitoring:** Budget alerts at 25%, 50%, 75%, 90%

---

## Competition-Specific: Auto-Shutdown

**Scenario:** Budget protection for 3-week competition window

**Implementation:** `local/auto-shutdown/`
- Cloud Function monitoring spend thresholds
- Automatic service shutdown at 90% budget ($216 of $240)
- Email notifications at each threshold
- One-command redeployment after shutdown

**Trade-offs Evaluated:**
- **Risk:** Service interruption during judge evaluation
- **Mitigation:** Set threshold at 90% (leaves $24 buffer)
- **Decision:** Manual monitoring preferred over auto-shutdown (judges could arrive any time)

---

## Development Workflow

### Local Development
```bash
# Backend: FastAPI with hot reload
cd backend && uvicorn app.main:app --reload

# Frontend: React dev server
cd frontend && npm start
```

### Deployment Pipeline
1. Code changes committed
2. Cloud Build triggered (automatic)
3. Multi-stage Docker build (frontend → backend bundle)
4. Deploy to Cloud Run (zero-downtime rolling update)
5. Health check verification

### Version Control
- **Git:** Feature branches, squash merges
- **Tagging:** Semantic versioning for releases
- **Rollback:** Cloud Run revision history (instant)

---

## Data Governance

### Privacy
- All driver IDs anonymized in source CSVs
- No personally identifiable information (PII) in telemetry
- Public demo-safe (no sensitive team data)

### Retention
- **Competition period:** Full data retention
- **Post-competition:** 30-day archive window
- **Cleanup:** One-command resource deletion

---

## Lessons Learned & Iteration

**Initial Approach:** Separate frontend/backend services
- **Issue:** CORS complexity, 2x deployment overhead
- **Iteration:** Bundled single service (Dockerfile multi-stage)

**Data Processing:** Tried real-time streaming
- **Issue:** Cost unpredictability, 10x complexity
- **Iteration:** Batch processing (one-time ML run, serve cached)

**Model Selection:** Evaluated multiple LLM providers
- **Decision:** Gemma 3 on Vertex AI
- **Rationale:** Open-source, cost-effective, sufficient quality

---

## Scalability Considerations

**Current Scale:**
- 14 races, 500+ vehicles
- 21,718 recommendations
- <100ms API response time

**Future Scale (if productionized):**
- Real-time telemetry ingestion (streaming)
- Multi-season historical analysis
- Live race strategy predictions
- Driver comparison heatmaps across seasons

**Architecture Supports:**
- Horizontal scaling (Cloud Run auto-scales)
- Data partitioning (Firestore subcollections)
- Caching layers (in-memory + CDN)
- A/B testing different ML models

---

## Operational Metrics

**Deployment Velocity:**
- Code to production: 4-8 minutes
- Zero-downtime rolling updates
- Instant rollback capability

**Reliability:**
- Health check: `/health` endpoint
- Uptime target: 99.9% during competition (3 weeks)
- Graceful degradation for missing data

**Cost Efficiency:**
- $60 for 3-week competition
- 75% below budget constraint

---

## Documentation Strategy

**External (GitHub):**
- `README.md` - Value proposition
- `docs/ML-APPROACH.md` - Technical depth for judges
- `docs/DEPLOYMENT.md` - Reproduction steps
- `docs/OPERATIONS.md` - This file (shows engineering maturity)

**Internal (`local/`):**
- `INTERNAL-CONTEXT.md` - Full project state for future dev
- Deployment scripts and utilities
- Data preparation tools

---

## Summary

This project demonstrates enterprise software practices applied at hackathon velocity:
- Cost optimization through strategic technology choices
- Reliability through configuration and monitoring
- Security through zero-credential architecture
- Scalability through serverless and batch processing
- Data quality through validation and graceful degradation

**Philosophy:** Build once with production mindset, rather than rebuild for production later.

---

**Operational Status:** Production-ready  
**Competition Period:** Nov 23 - Dec 12, 2025  
