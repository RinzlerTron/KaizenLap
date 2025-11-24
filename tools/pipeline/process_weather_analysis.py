"""
Weather Impact Analysis Job - Step 2b: Analyze Weather Impact

Purpose:
    Analyzes correlation between weather conditions and performance,
    identifies best performers in specific conditions, and saves insights to Firestore.

Usage:
    python process_weather_analysis.py <race_id>

    Or via environment variables:
    RACE_ID=1 python process_weather_analysis.py

Deployment:
    Runs as Cloud Run Job (CPU-only) using dockerfiles/telemetry-cpu.Dockerfile

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze weather impact on performance."
    )
    parser.add_argument("race_id", type=int, nargs='?', help="Race ID to analyze")
    
    args = parser.parse_args()
    
    # Get race_id from args or environment
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
            parser.error("race_id is required (provide as argument or set RACE_ID environment variable)")
    
    log.info("=" * 80)
    log.info("WEATHER IMPACT ANALYSIS JOB - STEP 2b: ANALYZE WEATHER IMPACT")
    log.info("=" * 80)
    log.info(f"Race ID: {race_id}")
    
    try:
        # Initialize analyser
        analyser = WeatherImpactAnalyser(race_id=race_id)
        
        # Run analysis
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






