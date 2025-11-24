"""
Pattern Analysis Job - Step 2c: Analyze Driver Patterns

Purpose:
    Analyzes driver consistency across multiple laps, identifies patterns and trends,
    detects strengths and weaknesses per section, and saves insights to Firestore.

Usage:
    python process_pattern_analysis.py <race_id> [--vehicle-id <id>]

    Or via environment variables:
    RACE_ID=1 VEHICLE_ID=5 python process_pattern_analysis.py

Deployment:
    Runs as Cloud Run Job (CPU-only) using dockerfiles/telemetry-cpu.Dockerfile

Input:
    - Race data from Firestore/PostgreSQL (laps, sections, timing)

Output:
    - Firestore: ml_pattern_recommendations collection
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
from pattern_analyser import PatternAnalyser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze driver consistency and patterns."
    )
    parser.add_argument("race_id", type=int, nargs='?', help="Race ID to analyze")
    parser.add_argument("--vehicle-id", type=int, help="Vehicle ID (optional, analyzes all if not specified)")
    
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
    
    vehicle_id = args.vehicle_id
    if not vehicle_id:
        vehicle_id_env = os.getenv("VEHICLE_ID")
        if vehicle_id_env:
            try:
                vehicle_id = int(vehicle_id_env)
            except ValueError:
                log.warning(f"Invalid VEHICLE_ID environment variable: {vehicle_id_env}")
    
    log.info("=" * 80)
    log.info("PATTERN ANALYSIS JOB - STEP 2c: ANALYZE DRIVER PATTERNS")
    log.info("=" * 80)
    log.info(f"Race ID: {race_id}")
    if vehicle_id:
        log.info(f"Vehicle ID: {vehicle_id}")
    else:
        log.info("Vehicle ID: All vehicles")
    
    try:
        # Initialize analyser
        analyser = PatternAnalyser(race_id=race_id, vehicle_id=vehicle_id)
        
        # Run analysis
        log.info("\n--- Step 2c/3: Analyzing Driver Patterns ---")
        results = analyser.run_analysis()
        
        log.info(f"\nPattern analysis complete. Generated {len(results)} recommendations.")
        log.info("Results saved to Firestore: ml_pattern_recommendations collection")
        
        if results:
            result = results[0]
            consistency = result.get("consistency_analysis", {})
            section_patterns = result.get("section_patterns", {})
            log.info("\nPattern Analysis Summary:")
            log.info(f"  Consistency Score: {consistency.get('consistency_score', 0):.1f}/10")
            log.info(f"  Improvement Trend: {consistency.get('improvement_trend', 'unknown')}")
            log.info(f"  Strengths: {len(section_patterns.get('strengths', []))} sections")
            log.info(f"  Weaknesses: {len(section_patterns.get('weaknesses', []))} sections")
        
    except Exception as e:
        log.error(f"Pattern analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()






