"""
Weather Impact Analysis Job - Step 2b: Analyze Weather Impact

Purpose:
    Analyzes correlation between weather conditions and performance,
    identifies best performers in specific conditions, and saves insights to Firestore.

Usage:
    # Single race (Cloud Run Job execution)
    python process_weather_analysis.py <race_id>
    
    # Batch mode (process all races)
    python process_weather_analysis.py --batch

    Or via environment variables:
    RACE_ID=1 python process_weather_analysis.py

Deployment:
    Runs as Cloud Run Job (CPU-only) using dockerfiles/telemetry-cpu.Dockerfile
    Executed via: gcloud run jobs execute process-weather-analysis --args="<race_id>"

Input:
    - Race data from Firestore/PostgreSQL (laps, timing)
    - Weather data from Firestore/PostgreSQL

Output:
    - Firestore: ml_weather_recommendations collection
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.config import settings
from weather_analyser import WeatherImpactAnalyser

# Google Cloud imports
try:
    from google.cloud import firestore
except ImportError:
    firestore = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def get_all_races_from_firestore():
    """Get all races from Firestore for batch processing."""
    if firestore is None:
        raise ImportError("google-cloud-firestore is not installed")
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("FIRESTORE_PROJECT_ID") or settings.PROJECT_ID
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT or FIRESTORE_PROJECT_ID must be set")
    
    database_id = os.getenv("FIRESTORE_DATABASE_ID", "kaizenlap-us")
    db = firestore.Client(project=project_id, database=database_id)
    races_ref = db.collection("races")
    
    races = []
    for race_doc in races_ref.stream():
        race_data = race_doc.to_dict()
        race_id = race_data.get("race_id") or race_data.get("id")
        if race_id:
            races.append(int(race_id))
    
    return sorted(races)


def process_single_race(race_id: int) -> int:
    """Process weather analysis for a single race."""
    try:
        log.info(f"\n{'='*60}")
        log.info(f"Processing Race {race_id}")
        log.info(f"{'='*60}")
        
        analyser = WeatherImpactAnalyser(race_id=race_id)
        results = analyser.run_analysis()
        
        if results:
            result = results[0]
            analysis = result.get("analysis", {})
            correlations_count = len(analysis.get("correlations", {})) if isinstance(analysis, dict) else 0
            log.info(f"✓ Race {race_id}: {correlations_count} correlations calculated")
            return 1
        else:
            log.warning(f"✗ Race {race_id}: No results generated")
            return 0
            
    except Exception as e:
        log.error(f"✗ Race {race_id} failed: {e}")
        return 0


def process_all_races():
    """Process all available races in batch mode (Cloud Run Job batch execution)."""
    log.info("=" * 80)
    log.info("CLOUD RUN JOB: WEATHER IMPACT ANALYSIS - BATCH MODE")
    log.info("=" * 80)
    
    all_races = get_all_races_from_firestore()
    log.info(f"Processing {len(all_races)} races total")
    
    successful_races = 0
    failed_races = 0
    
    for race_id in all_races:
        result = process_single_race(race_id)
        if result > 0:
            successful_races += 1
        else:
            failed_races += 1
    
    log.info(f"\n{'='*60}")
    log.info("BATCH WEATHER ANALYSIS COMPLETE")
    log.info(f"{'='*60}")
    log.info(f"Total races processed: {len(all_races)}")
    log.info(f"Successful: {successful_races}")
    log.info(f"Failed: {failed_races}")
    log.info("All results saved to Firestore: ml_weather_recommendations collection")
    
    if failed_races > 0:
        log.warning(f"⚠ {failed_races} races failed - check logs above")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze weather impact on performance."
    )
    parser.add_argument("--batch", action="store_true",
                        help="Process all races in batch mode (Cloud Run Job batch execution)")
    parser.add_argument("race_id", type=int, nargs='?', help="Race ID to analyze (ignored in batch mode)")
    
    args = parser.parse_args()
    
    if args.batch:
        # Batch processing mode - process all races
        process_all_races()
    else:
        # Single race mode - get race_id from args or environment
        race_id = args.race_id
        if not race_id:
            race_id_env = os.getenv("RACE_ID")
            if race_id_env:
                try:
                    race_id = int(race_id_env)
                except ValueError:
                    log.error(f"Invalid RACE_ID environment variable: {race_id_env}")
                    sys.exit(1)
            else:
                parser.error("race_id is required (provide as argument, set RACE_ID env var, or use --batch)")
        
        log.info("=" * 80)
        log.info("CLOUD RUN JOB: WEATHER IMPACT ANALYSIS - STEP 2b")
        log.info("=" * 80)
        log.info(f"Race ID: {race_id}")
        
        try:
            analyser = WeatherImpactAnalyser(race_id=race_id)
            log.info("\n--- Step 2b/3: Analyzing Weather Impact ---")
            results = analyser.run_analysis()
            
            log.info(f"\nWeather impact analysis complete. Generated {len(results)} recommendations.")
            log.info("Results saved to Firestore: ml_weather_recommendations collection")
            
            if results:
                result = results[0]
                analysis = result.get("analysis", {})
                log.info("\nWeather Impact Summary:")
                if analysis.get("correlations"):
                    log.info(f"  Correlations calculated: {len(analysis.get('correlations', {}))} metrics")
                if analysis.get("interpretation"):
                    log.info(f"  Interpretation: {analysis.get('interpretation', '')[:200]}...")
                if result.get("best_performer"):
                    bp = result.get("best_performer", {})
                    log.info(f"  Best Performer: Vehicle {bp.get('vehicle_id')}, "
                            f"Avg Lap Time: {bp.get('avg_lap_time_s', 0):.3f}s")
        
        except Exception as e:
            log.error(f"Weather impact analysis failed: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    main()






