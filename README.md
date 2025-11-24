# KaizenLap

**AI-Powered Racing Performance Coach for Toyota GR Cup**

Built as a complete entry for Toyota GR's **Hack the Track 2025**

---

## What It Does

KaizenLap turns official Toyota GR Cup race telemetry into a race engineer–grade coaching tool. It analyzes every section of every lap across 7 tracks and 14 races to tell a driver:

- **Where** they are losing time
- **Why** it’s happening (technique vs. conditions)
- **What** specific change to try next session

**For drivers:** Section-by-section coaching they can act on immediately  
**For engineers:** A fast way to triage issues and prioritize setup or coaching focus  
**For judges and fans:** A clear story of how the race unfolded beyond the final results

---

## How It Uses the TRD Datasets

KaizenLap is built around the Hack the Track telemetry and documentation, using the data as the single source of truth for all insights ([hackathon brief](https://hackthetrack.devpost.com/)):

- **144 telemetry CSVs** across **7 tracks / 14 races** (lap and section timing, positions, weather)
- **Best-case composite engine:** Builds a theoretical “perfect lap” from the fastest section times across the field
- **Section gap engine:** Computes deltas from the composite for every lap section for every driver
- **Weather & pattern engine:** Correlates temperature, humidity, wind and rain with pace and consistency
- **AI coaching engine (Gemma 3):** Converts raw statistics into fact-backed hypotheses and concrete recommendations

All insights are **pre-computed and stored in Firestore (21,718 documents)** so judges experience sub-100 ms responses rather than waiting for heavy analysis during a demo.

---

## Key Features for Judges

### Driver Training & Insights (Primary Category)
- **Best Case Composite Analysis:** Shows each driver’s theoretical potential lap vs. their actual best.
- **Section-by-Section Coaching (20K+ recs):** Pinpoints the exact corners where time is lost and suggests specific technique changes.
- **Pattern-Aware Coaching:** Uses Gemma 3 to separate observed facts from hypotheses and tie them to actionable next steps.

### Post-Event Analysis
- **Race Storytelling View:** Weather impact, consistency trends, and pace evolution across the full race distance.
- **Field Comparison:** Shows how a driver stacks up against the grid at a section and lap level, not just in final classification.

### Real-Time–Ready Architecture
- **Serverless pipeline on Cloud Run:** The same design can ingest streaming telemetry instead of historical CSVs.
- **Pre-computed insights:** Makes it realistic to surface AI coaching suggestions during a live race without blowing budget or latency.

---

## Product Experience & Design

The frontend is designed so a race engineer or driver can get value in under 60 seconds:

- **Interactive track maps:** SVG track maps with sector overlays and clear labeling of problem sections.
- **Lap and section comparison views:** Quickly switch between laps and see where pace improves or falls off.
- **Draggable recommendation panels:** Keep coaching insights visible while exploring the map and charts.
- **Toggleable analysis modes:** Four distinct analysis types (sections, weather, patterns, AI coaching) exposed through a simple toggle UI.
- **Judging-friendly:** All key flows are reachable from the landing view without configuration or credentials.

Implementation details:

- **Frontend:** React 18 + Material-UI  
- **Backend:** FastAPI serving both the API and static frontend  
- **Data & Storage:** Google Cloud Storage (raw CSVs), Firestore (indexed insights)

See `docs/ARCHITECTURE.md` and `docs/ML-APPROACH.md` for deeper technical diagrams and methodology.

---

## How It Works (End-to-End)

1. **Data ingestion:** Hack the Track CSVs are uploaded to Google Cloud Storage.  
2. **Batch analytics pipeline (5 jobs on Cloud Run):**  
   - Best-case composite generation  
   - Section gap analysis  
   - Weather correlation  
   - Driver pattern analysis  
   - Gemma 3 coaching synthesis  
3. **Storage:** 21,718 structured coaching documents written to Firestore with indexes tuned for sub-100 ms queries.  
4. **Serving layer:** FastAPI exposes a small, focused API surface that powers the React UI.  
5. **User flow:** Select track → select race → pick a driver and lap → explore sections and read targeted recommendations.

For detailed reproduction and deployment steps (including Cloud Run and Firestore setup), see `docs/DEPLOYMENT.md` and `docs/OPERATIONS.md`.

---

## How It Maps to Hack the Track Criteria

- **Application of TRD Datasets:** Uses the full telemetry package (lap, section, and weather data) to produce best-case composites, deltas, correlations, and AI-enhanced coaching—not just charts.  
- **Design:** A focused, judge-friendly UI with interactive maps, clear toggles for analysis modes, and minimal setup friction.  
- **Potential Impact:** Helps Toyota GR drivers and engineers prioritize coaching and setup changes, and provides a blueprint for extending to live race strategy tools.  
- **Quality & Novelty of Idea:** Combines traditional motorsport analytics with LLM-powered reasoning that explicitly separates **facts, theories, and actions**—bridging the gap between data and decision.


---

## Built With

Google Cloud Run • Firestore • Cloud Storage • Gemma 3 • React • FastAPI • Material-UI • Python (pandas, scikit-learn)

---

## License & Submission

This repository is the codebase for a **Hack the Track 2025** hackathon submission presented to Toyota Gazoo Racing and Devpost judges.

