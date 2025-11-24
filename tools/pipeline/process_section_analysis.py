"""
Section Analysis Job - Step 2: Analyze Section Performance

Purpose:
    Analyzes processed telemetry data to extract section-by-section KPIs,
    compares to best-case composite, and saves recommendations to Firestore.

Usage:
    python process_section_analysis.py <race_id> [--track-id <id>]

    Or via environment variables:
    RACE_ID=1 python process_section_analysis.py

Deployment:
    Runs as Cloud Run Job (CPU-only) using dockerfiles/telemetry-cpu.Dockerfile

Input:
    - Processed telemetry from GCS (from Step 1: process_telemetry_only.py)
    - Race data from Firestore/PostgreSQL
    - Best-case composite from Firestore/PostgreSQL

Output:
    - Firestore: ml_section_recommendations collection
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
from section_analyser import SectionAnalyser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

def get_all_races_from_firestore():
    """
    Get all processable races from Firestore.
    
    Returns:
        List of tuples: (race_id, track_name, race_number)
    """
    from google.cloud import firestore
    
    project_id = os.getenv('FIRESTORE_PROJECT_ID') or os.getenv('GCP_PROJECT_ID')
    db = firestore.Client(project=project_id)
    races_ref = db.collection("races")
    tracks_ref = db.collection("tracks")
    
    # Load all tracks first for lookup
    tracks = {}
    for track in tracks_ref.stream():
        track_data = track.to_dict()
        track_id = track_data.get('id')
        if track_id:
            tracks[track_id] = track_data.get('abbreviation') or track_data.get('name', '').lower()
    
    # Load all races
    race_list = []
    for race in races_ref.stream():
        race_data = race.to_dict()
        race_id = race_data.get('id')
        track_id = race_data.get('track_id')
        race_number = race_data.get('race_number', 1)
        
        if race_id and track_id:
            track_name = tracks.get(track_id, 'unknown')
            race_list.append((race_id, track_name, race_number))
            log.info(f"Found race {race_id}: {track_name} Race {race_number}")
    
    # Sort by race_id
    race_list.sort(key=lambda x: x[0])
    
    log.info(f"Loaded {len(race_list)} races from Firestore")
    return race_list


def process_single_race(race_id: int, track_name: str) -> int:
    """Process a single race and return the number of recommendations generated."""
    log.info(f"\n{'='*60}")
    log.info(f"Processing Race {race_id}: {track_name.upper()}")
    log.info(f"{'='*60}")

    try:
        # Initialize analyser
        analyser = SectionAnalyser(race_id=race_id, track_name=track_name)

        # Run analysis
        log.info("--- Analyzing Section Performance ---")
        results = analyser.run_analysis()

        recommendation_count = len(results) if results else 0
        log.info(f"✓ Race {race_id} ({track_name}) complete. Generated {recommendation_count} recommendations.")

        if results:
            high_impact_recs = [r for r in results if r.get("priority", {}).get("impact_score", 0) > 50]
            if high_impact_recs:
                log.info(f"  → {len(high_impact_recs)} high-impact recommendations found")

        return recommendation_count

    except Exception as e:
        log.error(f"✗ Race {race_id} ({track_name}) failed: {e}")
        return 0


def process_all_races():
    """Process all available races in batch mode."""
    log.info("🚀 STARTING BATCH SECTION ANALYSIS")
    
    # Get all races from Firestore (source of truth)
    all_races = get_all_races_from_firestore()
    log.info(f"Processing {len(all_races)} races total")

    total_recommendations = 0
    successful_races = 0
    failed_races = 0

    for race_id, track_name, race_number in all_races:
        rec_count = process_single_race(race_id, track_name)
        total_recommendations += rec_count

        if rec_count > 0:
            successful_races += 1
        else:
            failed_races += 1

    log.info(f"\n{'='*60}")
    log.info("BATCH ANALYSIS COMPLETE")
    log.info(f"{'='*60}")
    log.info(f"Total races processed: {len(all_races)}")
    log.info(f"Successful: {successful_races}")
    log.info(f"Failed: {failed_races}")
    log.info(f"Total recommendations: {total_recommendations}")
    log.info("All results saved to Firestore: ml_section_recommendations collection")

    if failed_races > 0:
        log.warning(f"⚠️ {failed_races} races failed - check logs above")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze section performance from processed telemetry."
    )
    parser.add_argument("--batch", action="store_true",
                       help="Process all available races instead of single race")
    parser.add_argument("--output-local", type=str,
                       help="Save output to local JSON file instead of Firestore (for testing)")
    parser.add_argument("race_id", type=int, nargs='?', help="Race ID to analyze (ignored in batch mode)")
    parser.add_argument("track_name", nargs='?', help="Track name (ignored in batch mode)")
    
    args = parser.parse_args()

    if args.batch:
        # Batch processing mode - process all races
        return process_all_races()

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
            parser.error("race_id is required (provide as argument or set RACE_ID env var)")

    # Get track_name from args or environment
    track_name = args.track_name
    if not track_name:
        track_name_env = os.getenv("TRACK_NAME")
        if track_name_env:
            track_name = track_name_env
        else:
            parser.error("track_name is required (provide as argument or set TRACK_NAME env var)")

    log.info("=" * 80)
    log.info("SECTION ANALYSIS JOB - STEP 2a: ANALYZE SECTION PERFORMANCE")
    log.info("=" * 80)
    log.info(f"Race ID: {race_id}")
    log.info(f"Track Name: {track_name}")
    
    try:
        # Initialize analyser
        analyser = SectionAnalyser(race_id=race_id, track_name=track_name)
        
        # Run analysis
        log.info("\n--- Step 2a/3: Analyzing Section Performance ---")
        results = analyser.run_analysis()
        
        log.info(f"\nSection analysis complete. Generated {len(results)} recommendations.")
        
        # Save to local file or Firestore
        if args.output_local:
            # Save to local JSON file for testing
            import json
            from pathlib import Path
            output_path = Path(args.output_local)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            log.info(f"Results saved to local file: {args.output_local}")
        else:
            # Save to Firestore (production)
            if results:
                analyser._save_recommendations_to_firestore(results)
                log.info("Results saved to Firestore: ml_section_recommendations collection")
            else:
                log.warning("No results to save")
        
        if results:
            high_impact_recs = [r for r in results if r.get("priority", {}).get("impact_score", 0) > 50]
            log.info(f"  Found {len(high_impact_recs)} high-impact recommendations.")
            if high_impact_recs:
                rec = high_impact_recs[0]
                log.info(f"  Example: Lap {rec.get('lap_number')}, Section {rec.get('section_name')}, "
                         f"Time Loss: {rec.get('time_loss_s')}s")
        
    except Exception as e:
        log.error(f"Section analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

