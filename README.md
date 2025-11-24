# KaizenLap

<div align="center">

![Google Cloud](https://img.shields.io/badge/Google%20Cloud-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![Gemma 3](https://img.shields.io/badge/Gemma%203-FF6F00?style=for-the-badge&logo=google&logoColor=white)

</div>

*"Kaizen" (改善) - Japanese for "continuous improvement." That's what racing is all about.*

**AI-Powered Racing Performance Coach for Toyota GR Cup**

Built for **Hack the Track 2025**

---

## What It Does

KaizenLap turns official Toyota GR Cup race telemetry into a race engineer–grade coaching tool. It analyzes every section of every lap across 7 tracks and 14 races to tell a driver:

- **Where** they are losing time
- **Why** it's happening (technique vs. conditions)
- **What** specific change to try next session

**For drivers:** Section-by-section coaching they can act on immediately  
**For engineers:** A fast way to triage issues and prioritize setup or coaching focus  
**For judges:** A clear story of how the race unfolded beyond the final results

**Example coaching output:**  
*"You're 0.5 seconds slower in Section 2 (Turns 4-6). Your lap-to-lap variability here is 0.7s—significantly higher than the field average of 0.2s. This pattern suggests front-end grip inconsistency. Data hypothesis: You're carrying too much speed into the braking zone, destabilizing the platform. Recommendation: Brake 10 meters earlier to settle the car before turn-in. Monitor Section 2 consistency over the next 3 laps."*

That's not generic advice. That's race-grade coaching backed by statistical analysis of the entire field's performance.

---

## How It Uses the TRD Datasets

KaizenLap is built around the Hack the Track telemetry and documentation, using the data as the single source of truth for all insights ([hackathon brief](https://hackthetrack.devpost.com/)):

- **144 telemetry CSVs** across **7 tracks / 14 races** (lap and section timing, positions, weather)
- **Best-case composite engine:** Builds a theoretical "perfect lap" from the fastest section times across the field
- **Section gap engine:** Computes deltas from the composite for every lap section for every driver
- **Weather & pattern engine:** Correlates temperature, humidity, wind and rain with pace and consistency
- **AI coaching engine (Gemma 3):** Converts raw statistics into fact-backed hypotheses and concrete recommendations

The system focuses on Race 1 and Race 2 from each track—these races represent the most complete and consistent data structure across the dataset, providing the strongest foundation for comparative analysis and coaching quality.

All insights are **pre-computed and stored in Firestore (21,718 documents)** so judges experience sub-100 ms responses rather than waiting for heavy analysis during a demo.

---

## Key Features for Judges

### Driver Training & Insights (Primary Category)
- **Best Case Composite Analysis:** Shows each driver's theoretical potential lap vs. their actual best
- **Section-by-Section Coaching (20K+ recs):** Pinpoints the exact corners where time is lost and suggests specific technique changes
- **Pattern-Aware Coaching:** Uses Gemma 3 to separate observed facts from hypotheses and tie them to actionable next steps

### Post-Event Analysis
- **Race Storytelling View:** Weather impact, consistency trends, and pace evolution across the full race distance
- **Field Comparison:** Shows how a driver stacks up against the grid at a section and lap level, not just in final classification

### Real-Time–Ready Architecture
- **Serverless pipeline on Cloud Run:** The same design can ingest streaming telemetry instead of historical CSVs
- **Pre-computed insights model:** Demonstrates how AI coaching can be delivered with split-second response times—critical for live race strategy decisions (optimal pit windows, tire degradation tracking, competitor pace analysis)

---

## Product Experience & Design

The frontend is designed so a race engineer or driver can get value in under 60 seconds:

- **Interactive track maps:** SVG track maps with sector overlays and clear labeling of problem sections
- **Lap and section comparison views:** Quickly switch between laps and see where pace improves or falls off
- **Draggable recommendation panels:** Keep coaching insights visible while exploring the map and charts
- **Toggleable analysis modes:** Four distinct analysis types (sections, weather, patterns, AI coaching) exposed through a simple toggle UI
- **Judging-friendly:** All key flows are reachable from the landing view without configuration or credentials

---

## How It Works

**Step 1:** Analytics pipeline processes telemetry CSVs to build statistical foundation (best-case composites, section gaps, weather correlations, pattern detection)

**Step 2:** Gemma 3 AI synthesizes the raw analytics into structured coaching insights, separating observable facts from theoretical explanations

**Step 3:** All insights stored in Firestore for instant retrieval

**Step 4:** React UI lets users select track → race → driver → lap and explore coaching recommendations

See `docs/ARCHITECTURE.md` for technical implementation details and `docs/ML-APPROACH.md` for AI methodology.

---

## How It Maps to Hack the Track Criteria

### Application of TRD Datasets (40%)
Uses 100% of the telemetry structure (lap times, section times, weather, positions). Doesn't just visualize—generates new derivative insights like best-case composites and AI coaching that don't exist in the raw data. Every one of 21,718 recommendations traces back to specific CSV records.

### Design (20%)
A focused, judge-friendly UI with interactive maps, clear toggles for analysis modes, and minimal setup friction. Optimized for 60-second time-to-insight—judges can explore a driver's race without reading documentation.

### Potential Impact (30%)
Helps Toyota GR drivers and engineers prioritize coaching and setup changes post-session. Provides a blueprint for extending to live race strategy tools—imagine race engineers getting AI recommendations during a live session with split-second strategic intelligence that could mean the difference between a podium and fifth place.

### Quality & Novelty of Idea (10%)
Combines traditional motorsport analytics with LLM-powered reasoning that explicitly separates **facts, theories, and actions**—bridging the gap between data and decision. Novel application of open-source Gemma 3 makes this economically viable at scale.

---

## Categories Addressed

KaizenLap competes primarily in **Driver Training & Insights** but demonstrates capabilities across multiple competition categories:

### ⭐ Primary: Driver Training & Insights
- **20,907 section-specific coaching recommendations**: Every lap section analyzed across all drivers with AI-generated improvement strategies
- **Root cause analysis**: AI separates driver technique issues from setup problems and environmental factors
- **Actionable intelligence**: Not "you're slow here" but "you're slow here because of X, try Y"

### Secondary: Post-Event Analysis
- **Complete race reconstruction**: Weather correlation, consistency trends, pace evolution across full race distance
- **Field comparison**: Shows how each driver performs relative to the theoretical best-case composite, not just against the race winner
- **Data storytelling**: Visualizes the race through interactive track maps with section-level performance overlay

### Tertiary: Real-Time Analytics (Architecture Proven)
- **Pre-computed insights model**: Demonstrates how AI coaching can be delivered with sub-100ms latency
- **Serverless pipeline**: Same infrastructure handles batch historical analysis or streaming live telemetry
- **Race-ready design**: Built to extend from post-session review to in-session strategy tool

---

## Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Technical implementation, data pipeline, system design
- **[ML-APPROACH.md](docs/ML-APPROACH.md)** - AI methodology, algorithm selection, coaching synthesis
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Step-by-step reproduction guide

---

## Built With

Google Cloud Run • Firestore • Cloud Storage • Gemma 3 • React • FastAPI • Material-UI • Python (pandas, scikit-learn)

---

## License & Submission

This repository is the codebase for a **Hack the Track 2025** hackathon submission presented to Toyota Gazoo Racing and Devpost judges.

**License:** MIT
