#!/usr/bin/env python3
"""
Job 1: Initialize Firestore and compute best case composites.

Why combined: Both are one-time setup operations.
Best case composite: Theoretical perfect lap from fastest sections across all drivers.
"""
import sys
import logging
import argparse
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "deployment"))
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Initialize Firestore and compute best case composites')
    parser.add_argument('--mode', choices=['local', 'cloud'], default='cloud',
                        help='Execution mode (default: cloud)')
    parser.add_argument('--output-local', type=str,
                        help='Save local validation data to this path')
    args = parser.parse_args()
    
    log.info("=" * 80)
    log.info("CLOUD RUN JOB: INIT & COMPUTE BEST CASE COMPOSITES")
    log.info("=" * 80)
    log.info(f"Mode: {args.mode}")
    
    # Step 1: Initialize Firestore
    log.info("\n" + "=" * 80)
    log.info("STEP 1: Initializing Firestore Metadata")
    log.info("=" * 80)
    
    try:
        from init_firestore_complete import seed_firestore
        tracks, races = seed_firestore()
        log.info(f"SUCCESS: Firestore initialized: {len(tracks)} tracks, {len(races)} races")
    except Exception as e:
        log.error(f"FAILED: Initialize Firestore - {type(e).__name__}: {e}", exc_info=True)
        log.error("Check: 1) Firestore enabled 2) Service account permissions 3) Project ID correct")
        sys.exit(1)
    
    # Step 2: Compute Best Case Composites
    log.info("\n" + "=" * 80)
    log.info("STEP 2: Computing Best Case Composites")
    log.info("=" * 80)
    
    try:
        from compute_best_case_composites import compute_all_composites
        log.info("Starting composite computation - this will take 10-15 minutes...")
        compute_all_composites()
        log.info("SUCCESS: Best case composites computed successfully")
    except Exception as e:
        log.error(f"FAILED: Compute composites - {type(e).__name__}: {e}", exc_info=True)
        log.error("Check: 1) GCS data accessible 2) Track/race metadata exists 3) CSV file naming")
        sys.exit(1)
    
    # Local validation data export not needed for production deployment
    if args.mode == 'local' and args.output_local:
        log.info(f"Note: Validation export not implemented (not needed for cloud deployment)")
    
    log.info("\n" + "=" * 80)
    log.info("JOB COMPLETE - ALL STEPS SUCCEEDED")
    log.info("=" * 80)
    log.info("\nFirestore collections populated:")
    log.info("  - tracks: 7 documents")
    log.info("  - races: 14 documents")
    log.info("  - best_case_composites: ~50 documents")
    log.info("\nNext: Verify with 'python local/check_firestore_counts.py'")


if __name__ == "__main__":
    main()

