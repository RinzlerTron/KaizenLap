#!/usr/bin/env python3
"""
Gemma 3 Coaching Enhancement - ML-powered performance insights.

Aggregates lap-by-lap data per driver and sends to Gemma 3 LLM for analysis.
Gemma discovers patterns, diagnoses root causes, and generates evidence-based coaching.

Why: Template recommendations state facts. Gemma discovers WHY patterns exist.
How: Send raw lap times → Gemma analyzes → Evidence-based coaching returned.
"""
import os
import sys
import json
import time
import argparse
import logging
import requests
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
from google.cloud import firestore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('FIRESTORE_PROJECT_ID', 'your-project-id')
DATABASE_ID = os.getenv('FIRESTORE_DATABASE_ID', 'kaizenlap-us')
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

def get_best_case_for_race(race_id):
    """Get best case composite for race (for comparison)."""
    composites = db.collection('best_case_composites')\
        .where('race_id', '==', race_id)\
        .where('is_active', '==', True)\
        .stream()
    
    best_case = {}
    for comp in composites:
        data = comp.to_dict()
        section = data.get('section_name')
        if section:
            best_case[section] = {
                'time_s': data.get('best_time_ms', 0) / 1000.0,
                'vehicle': data.get('source_vehicle_id', 'unknown')
            }
    return best_case

def get_lap_by_lap_data(race_id, vehicle_id):
    """Extract lap-by-lap section times (RAW DATA, no aggregation)."""
    log.info(f"  Extracting lap-by-lap data...")
    
    # Get all section recommendations for this vehicle
    sections = db.collection('ml_section_recommendations')\
        .where('race_id', '==', race_id)\
        .where('vehicle_id', '==', vehicle_id)\
        .stream()
    
    # Group by lap number
    laps = defaultdict(dict)
    
    for sec in sections:
        data = sec.to_dict()
        lap_num = data.get('lap_number')
        section_name = data.get('section_name')
        section_time = data.get('driver_kpis', {}).get('section_time_s')
        
        if lap_num and section_name and section_time:
            laps[lap_num][section_name] = section_time
    
    # Convert to sorted list
    lap_list = []
    for lap_num in sorted(laps.keys()):
        lap_data = {'lap': lap_num}
        lap_data.update(laps[lap_num])
        
        # Calculate lap total if all sections present
        if 'Section 1' in laps[lap_num] and 'Section 2' in laps[lap_num] and 'Section 3' in laps[lap_num]:
            lap_data['total'] = round(sum(laps[lap_num].values()), 2)
        
        lap_list.append(lap_data)
    
    log.info(f"    Found {len(lap_list)} complete laps")
    return lap_list

def get_field_best_performers(race_id):
    """Get fastest driver per section for comparison."""
    sections = db.collection('ml_section_recommendations')\
        .where('race_id', '==', race_id)\
        .stream()
    
    best_per_section = {}
    for sec in sections:
        data = sec.to_dict()
        section = data.get('section_name')
        vehicle = data.get('vehicle_id')
        time = data.get('driver_kpis', {}).get('section_time_s')
        
        if section and time:
            if section not in best_per_section or time < best_per_section[section]['time']:
                best_per_section[section] = {'vehicle': vehicle, 'time': round(time, 2)}
    
    return best_per_section

def aggregate_for_gemma(race_id, vehicle_id):
    """Aggregate data for Gemma analysis - RAW DATA, minimal processing."""
    race_doc = db.collection('races').document(str(race_id)).get()
    if not race_doc.exists:
        return None
    
    race_data = race_doc.to_dict()
    track_name = race_data.get('track_name', 'Unknown')
    
    # Weather
    weather_doc = db.collection('ml_weather_recommendations')\
        .document(f'race_{race_id}_weather_impact').get()
    weather = weather_doc.to_dict() if weather_doc.exists else {}
    weather_summary = weather.get('weather_summary', {})
    
    # Best case composite
    best_case = get_best_case_for_race(race_id)
    
    # Field best performers
    field_best = get_field_best_performers(race_id)
    
    # THIS DRIVER's lap-by-lap data (RAW)
    lap_data = get_lap_by_lap_data(race_id, vehicle_id)
    
    if not lap_data:
        log.warning("No lap data found")
        return None
    
    return {
        'race_id': race_id,
        'vehicle_id': vehicle_id,
        'track_name': track_name,
        'weather': {
            'temp_c': round(weather_summary.get('avg_air_temp_celsius', 0), 1),
            'humidity': round(weather_summary.get('avg_humidity_percent', 0), 1),
            'wind_kmh': round(weather_summary.get('avg_wind_speed', 0), 1)
        },
        'best_case_composite': best_case,
        'field_best_performers': field_best,
        'lap_by_lap_data': lap_data  # RAW lap times, let Gemma analyze
    }

def generate_coaching_with_gemma(context, endpoint_url):
    """Call Gemma with RAW data - let IT discover patterns."""
    
    # Build unbiased prompt - give data, ask for insights
    prompt = f"""You are a racing performance analyst with expertise in driver coaching.

**Race:** {context['track_name']} (Race {context['race_id']})
**Weather:** {context['weather']['temp_c']}°C, {context['weather']['humidity']}% humidity

**Best Possible Times (Best Case Composite):**
"""
    
    for section, data in context['best_case_composite'].items():
        prompt += f"\n- {section}: {data['time_s']:.2f}s"
    
    prompt += f"""

**Top Performers in This Race:**
"""
    
    for section, data in context['field_best_performers'].items():
        prompt += f"\n- {section}: Vehicle {data['vehicle']} ({data['time']:.2f}s)"
    
    prompt += f"""

**Vehicle {context['vehicle_id']} - Lap-by-Lap Performance:**

"""
    
    # Show lap data in table format
    prompt += "Lap | Section 1 | Section 2 | Section 3 | Total\n"
    prompt += "----|-----------|-----------|-----------|-------\n"
    
    for lap in context['lap_by_lap_data'][:20]:  # First 20 laps to fit token limit
        s1 = lap.get('Section 1', 0)
        s2 = lap.get('Section 2', 0)
        s3 = lap.get('Section 3', 0)
        total = lap.get('total', 0)
        prompt += f"{lap['lap']:3d} | {s1:7.2f}s  | {s2:7.2f}s  | {s3:7.2f}s  | {total:.2f}s\n"
    
    prompt += f"""

**Your Task:**
Analyze this lap-by-lap data. Be EVIDENCE-BASED - distinguish facts from theories.

**CRITICAL CONSTRAINTS:**
1. FACTS ONLY: State what the numbers PROVE (lap X is Y seconds)
2. THEORIES: Clearly label speculation with "This could indicate..." or "Possible causes include..."
3. SEPARATE: Keep observed data and theories in different fields
4. CITE: Reference specific lap numbers as evidence

**Analysis:**
1. DATA OBSERVATIONS: What do the numbers show? (lap X: time Y, lap Z: time W)
2. PATTERNS: What changes over time? (improving? degrading? variable?)
3. THEORIES: What MIGHT explain this? (list 2-3 possibilities, not certainties)

**Recommendations:**
Focus on what driver can MEASURE and CHANGE. Reference lap numbers that prove the recommendation.

**Return ONLY valid JSON:**
{{
  "data_facts": {{
    "observable_pattern": "what lap times show (cite laps)",
    "worst_section": "section with most time loss (cite laps and times)",
    "best_lap_analysis": "what lap X shows is possible"
  }},
  "theories": {{
    "possible_cause_1": "theory based on pattern",
    "possible_cause_2": "alternative theory",
    "confidence": "low/medium/high based on data clarity"
  }},
  "recommendations": [
    {{
      "priority": 1,
      "focus": "specific section or aspect",
      "data_evidence": "lap X shows Y, lap Z shows W",
      "theory": "this MIGHT be because...",
      "action": "specific technique to try",
      "measurement": "what to track to verify if this helps"
    }},
    {{
      "priority": 2,
      "focus_area": "...",
      "diagnosis": "...",
      "technique": "...",
      "expected_gain": "..."
    }},
    {{
      "priority": 3,
      "focus_area": "...",
      "diagnosis": "...",
      "technique": "...",
      "expected_gain": "..."
    }}
  ]
}}
"""
    
    # Call Gemma
    try:
        log.info(f"  Sending {len(prompt)} chars to Gemma...")
        response = requests.post(
            f"{endpoint_url}/api/generate",
            json={"model": "gemma3:4b", "prompt": prompt, "stream": False},
            timeout=120
        )
        
        if response.status_code != 200:
            log.error(f"Gemma failed: {response.status_code}")
            return None
        
        result = response.json()
        text = result.get('response', '')
        
        # Extract JSON
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            text = text[start:end].strip()
        elif '{' in text:
            start = text.find('{')
            end = text.rfind('}') + 1
            text = text[start:end]
        
        return json.loads(text)
        
    except Exception as e:
        log.error(f"Error: {e}")
        return None

def save_to_firestore(context, coaching):
    """Save coaching with context."""
    doc_id = f"race_{context['race_id']}_vehicle_{context['vehicle_id']}"
    
    db.collection('coaching_insights').document(doc_id).set({
        'race_id': context['race_id'],
        'vehicle_id': context['vehicle_id'],
        'track_name': context['track_name'],
        'data_sent_to_gemma': {
            'weather': context['weather'],
            'best_case': context['best_case_composite'],
            'field_best': context['field_best_performers'],
            'total_laps': len(context['lap_by_lap_data'])
        },
        'gemma_analysis': coaching,
        'created_at': firestore.SERVER_TIMESTAMP,
        'version': 'v3_unbiased_lap_analysis'
    })

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--endpoint', type=str,
                        default=os.getenv('GEMMA_ENDPOINT'),
                        help='Gemma endpoint')
    parser.add_argument('--limit', type=int, help='Limit for testing')
    parser.add_argument('--retry-failed', action='store_true',
                        help='Only process vehicles missing coaching insights')
    args = parser.parse_args()
    
    if not args.endpoint:
        log.error("Need --endpoint")
        return
    
    log.info("=" * 80)
    log.info("GEMMA 3 COACHING - UNBIASED LAP-BY-LAP ANALYSIS")
    log.info("=" * 80)
    
    # Get all vehicles
    patterns = db.collection('ml_pattern_recommendations').stream()
    all_vehicles = [{'race_id': p.to_dict()['race_id'], 'vehicle_id': p.to_dict()['vehicle_id']} 
                    for p in patterns]
    
    # Filter for retry if requested
    if args.retry_failed:
        existing = set()
        for doc in db.collection('coaching_insights').stream():
            d = doc.to_dict()
            existing.add((d['race_id'], d['vehicle_id']))
        
        vehicles = [v for v in all_vehicles 
                    if (v['race_id'], v['vehicle_id']) not in existing]
        log.info(f"Retry mode: {len(vehicles)} vehicles missing coaching")
    else:
        vehicles = all_vehicles
    
    if args.limit:
        vehicles = vehicles[:args.limit]
    
    log.info(f"Processing {len(vehicles)} vehicles...\n")
    
    success = 0
    for i, v in enumerate(vehicles, 1):
        log.info(f"[{i}/{len(vehicles)}] Race {v['race_id']}, Vehicle {v['vehicle_id']}")
        
        try:
            context = aggregate_for_gemma(v['race_id'], v['vehicle_id'])
            if not context:
                continue
            
            coaching = generate_coaching_with_gemma(context, args.endpoint)
            if coaching:
                save_to_firestore(context, coaching)
                success += 1
                log.info(f"  ✓ Primary issue: {coaching.get('analysis', {}).get('primary_issue', 'N/A')[:60]}...")
            
            time.sleep(2)
            
        except Exception as e:
            log.error(f"  ✗ Error: {e}")
    
    log.info(f"\n✓ Complete: {success}/{len(vehicles)} processed")

if __name__ == "__main__":
    main()
