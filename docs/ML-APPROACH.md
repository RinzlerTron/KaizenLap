# KaizenLap ML Approach

## Overview

KaizenLap uses AI to transform raw racing telemetry into actionable driver coaching. The system analyzes 21,000+ lap sections across 7 tracks and 14 races from the 2024 Toyota GR Cup season, delivering four distinct types of insights that help drivers improve performance.

## Why Machine Learning?

Traditional racing analysis relies on human engineers manually reviewing timing sheets. This approach:
- Misses subtle patterns across hundreds of laps
- Can't correlate weather conditions with performance degradation
- Takes hours to analyze what AI can process in minutes
- Focuses on "what happened" rather than "why it happened"

**KaizenLap's AI identifies patterns humans miss** and provides evidence-based explanations for performance variations.

## The Four Analysis Engines

### 1. **Best Case Composite Analysis**
**What it does:** Combines the fastest section times from all drivers to create a theoretical "perfect lap"  
**Why it matters:** Shows each driver their true potential – what's actually achievable on that track, in those conditions  
**Technical approach:** Statistical aggregation of 20,000+ section times per race

### 2. **Section Analysis** (20,907 recommendations)
**What it does:** Compares every lap section to the best case and identifies specific corners where time is being lost  
**Why it matters:** Pinpoints exactly where to focus – "You're 0.5s slower in Section 2"  
**Technical approach:** Real-time delta calculations with statistical significance testing

### 3. **Weather Impact Analysis** (14 recommendations)
**What it does:** Correlates air temperature, humidity, wind speed, and rain with lap time variations  
**Why it matters:** Helps teams anticipate performance changes as conditions evolve during a race  
**Technical approach:** Multi-variate correlation analysis across weather sensors and lap timing

### 4. **Driver Pattern Analysis** (357 recommendations)
**What it does:** Tracks lap-to-lap consistency, identifies improvement/degradation trends, and calculates consistency scores  
**Why it matters:** Reveals whether a driver is improving, fading, or maintaining pace – critical for race strategy  
**Technical approach:** Time series analysis with standard deviation modeling

### 5. **Gemma 3 AI Coaching** (357 insights)
**The game-changer:** All statistical analysis feeds into Google's Gemma 3 LLM, which:
- Reads lap-by-lap progression data
- Separates observable facts from theories
- Diagnoses root causes (e.g., "High Section 2 variability suggests front-end grip issues")
- Provides specific, actionable techniques (e.g., "Experiment with earlier throttle application")

**Why Gemma 3:** Open-source model deployed on Cloud Run with L4 GPU, enabling real-time insights without API rate limits or cost concerns.

## Data Pipeline

```
CSV Telemetry (GCS) → 5 Cloud Run Jobs → Firestore → FastAPI Backend → React Frontend
```

**Scale:** 21,718 documents processed from 14 races, served via API in <100ms

**Architecture:** Serverless (Cloud Run), auto-scaling from 1-2 instances, 2-minute average response time

## What Makes This Different

**Not just a dashboard:** KaizenLap doesn't just visualize data – it interprets it. The AI understands racing context:
- Recognizes when slow section times indicate setup issues vs. driver technique
- Identifies when weather is affecting tire grip
- Separates pace degradation from traffic delays

**Evidence-based coaching:** Every recommendation includes:
- The data that led to the insight
- The theoretical explanation
- A specific action to take

**Real-time ready:** While this demo uses historical data, the architecture is designed for live race telemetry – engineers could see AI coaching insights as the race unfolds.

## Categories Addressed

✅ **Driver Training & Insights:** Section-specific coaching with AI-powered root cause analysis  
✅ **Post-Event Analysis:** Complete race dashboard with 4 analysis types  
✅ **Wildcard:** Novel application of LLM for racing strategy (Gemma 3 for coaching)

## Technical Stack

**Frontend:** React + Material-UI  
**Backend:** FastAPI + Firestore  
**ML Pipeline:** Cloud Run Jobs + Gemma 3 (4B model, L4 GPU)  
**Data:** 7 tracks, 14 races, 500+ vehicles, 21K+ analyzed sections

---

**Built for the Hack the Track 2025 competition**  
Real Toyota GR Cup data. Real AI insights. Real impact on driver performance.
