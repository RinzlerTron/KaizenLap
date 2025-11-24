"""
Compute Best-Case Composite Script

Computes and stores best-case composites:
1. Per-track (across all races for that track)
2. Per-race (for individual races)

Saves to Firestore for Cloud Run deployment.

This reads directly from GCS CSV files (23_*.CSV) and processed telemetry files,
eliminating dependency on Firestore lap_sections collection.

This should be run AFTER telemetry processing is complete.
"""

import sys
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Add tools/pipeline to path for imports
tools_pipeline_path = Path(__file__).parent
sys.path.insert(0, str(tools_pipeline_path))

from app.config import settings
from app.utils.gpu_utils import pd
from app.utils.track_names import get_track_id, normalize_to_folder_name

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

try:
    from google.cloud import firestore, storage
    from google.auth.exceptions import DefaultCredentialsError
    from google.api_core.exceptions import NotFound
except ImportError:
    firestore = None
    storage = None
    DefaultCredentialsError = Exception
    NotFound = FileNotFoundError

# Import pipeline utilities (after adding tools/pipeline to path)
from gcs_reader import load_lap_sections_from_gcs, get_race_info_from_firestore, construct_gcs_path
from track_manager import Track
import ml_config

def get_firestore_client():
    """Get Firestore client."""
    if firestore is None:
        raise ImportError("google-cloud-firestore not installed")
    
    # Try environment variable first, then settings
    project_id = os.getenv("FIRESTORE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
    if not project_id:
        project_id = settings.FIRESTORE_PROJECT_ID or settings.PROJECT_ID
    
    if not project_id:
        raise ValueError("FIRESTORE_PROJECT_ID or PROJECT_ID must be set")
    
    log.info(f"Initializing Firestore client with project: {project_id}")
    return firestore.Client(project=project_id)

def _load_processed_telemetry_from_gcs(race_id: int) -> pd.DataFrame:
    """Load processed telemetry from GCS for a specific race."""
    db = get_firestore_client()
    doc_ref = db.collection("processed_telemetry").document(f"race_{race_id}")
    
    try:
        doc = doc_ref.get()
        if not doc.exists:
            raise ValueError(f"No processed telemetry found for race {race_id}")
    except NotFound:
        raise ValueError(f"Firestore document not found for race {race_id}")
    
    doc_data = doc.to_dict()
    gcs_path = doc_data.get("gcs_path")
    
    if not gcs_path:
        raise ValueError(f"No GCS path found in processed_telemetry document for race {race_id}")
    
    log.info(f"Loading processed telemetry from {gcs_path}")
    df = pd.read_csv(gcs_path)
    log.info(f"Loaded {len(df)} rows from processed telemetry")
    return df


def _extract_kpis_for_section(section_df: pd.DataFrame) -> Dict:
    """Extract KPIs from telemetry section (reused from section_analyser logic)."""
    if section_df.empty:
        return {}
    
    kpis = {}
    
    # Speed KPIs
    if 'Speed' in section_df.columns:
        kpis['apex_speed_kph'] = float(section_df['Speed'].min())
        kpis['max_speed_kph'] = float(section_df['Speed'].max())
        kpis['avg_speed_kph'] = float(section_df['Speed'].mean())
    
    # Braking KPIs
    if 'pbrake_f' in section_df.columns:
        brake_threshold = ml_config.kpi_thresholds["brake_pressure"]
        braking_points = section_df[section_df['pbrake_f'] > brake_threshold]
        if not braking_points.empty:
            kpis['braking_point_m'] = float(braking_points.iloc[0]['Laptrigger_lapdist_dls'])
        else:
            kpis['braking_point_m'] = -1
    
    # Throttle KPIs
    if 'ath' in section_df.columns:
        throttle_threshold = ml_config.kpi_thresholds["throttle_application"]
        throttle_points = section_df[section_df['ath'] > throttle_threshold]
        if not throttle_points.empty:
            kpis['throttle_on_point_m'] = float(throttle_points.iloc[0]['Laptrigger_lapdist_dls'])
        else:
            kpis['throttle_on_point_m'] = -1
        
        kpis['time_on_throttle_pct'] = float((section_df['ath'] > throttle_threshold).mean() * 100)
    
    # Brake time percentage
    if 'pbrake_f' in section_df.columns:
        kpis['time_on_brake_pct'] = float((section_df['pbrake_f'] > ml_config.kpi_thresholds["time_on_brake"]).mean() * 100)
    
    # Lateral G (if available)
    if 'accy_can' in section_df.columns:
        kpis['max_lateral_g'] = float(section_df['accy_can'].abs().max())
    
    return kpis


def compute_composite_from_gcs(track_id: int, race_id: int = None) -> Dict:
    """
    Compute best-case composite from GCS CSV files and processed telemetry.
    
    Args:
        track_id: Track ID (for track-level composite)
        race_id: Race ID (for race-level composite, optional)
    
    Returns:
        Dictionary mapping section_name to best-case data with KPIs
    """
    db = get_firestore_client()
    
    # Get track info
    track_ref = db.collection("tracks").document(str(track_id))
    track_doc = track_ref.get()
    if not track_doc.exists:
        # Try querying by id field
        track_query = db.collection("tracks").where("id", "==", track_id).limit(1)
        track_docs = list(track_query.stream())
        if not track_docs:
            log.warning(f"Track {track_id} not found in Firestore")
            return {}
        track_data = track_docs[0].to_dict()
    else:
        track_data = track_doc.to_dict()
    
    track_name = track_data.get("abbreviation") or track_data.get("name", "").lower()
    
    # Get race IDs to process
    if race_id:
        race_ids = [race_id]
    else:
        # Get all races for this track
        races_ref = db.collection("races")
        races_query = races_ref.where("track_id", "==", track_id)
        race_ids = [int(race.id) if race.id.isdigit() else race.to_dict().get("id") for race in races_query.stream()]
    
    if not race_ids:
        log.warning(f"No races found for track {track_id}")
        return {}
    
    log.info(f"Processing {len(race_ids)} races for track {track_name}")
    
    # Step 1: Aggregate all section times from CSV files
    all_laps_list = []
    race_info_map = {}  # Map race_id to race_number and track_name
    
    for rid in race_ids:
        try:
            race_info = get_race_info_from_firestore(rid, db)
            if not race_info:
                log.warning(f"Could not get race info for race {rid}, skipping")
                continue
            
            race_number = race_info.get("race_number", 1)
            race_info_map[rid] = race_info
            
            # Read CSV from GCS
            sections_df = load_lap_sections_from_gcs(track_name, race_number)
            sections_df['race_id'] = rid
            all_laps_list.append(sections_df)
            log.info(f"Loaded {len(sections_df)} rows from race {rid}")
        except Exception as e:
            log.warning(f"Could not load CSV for race {rid}: {e}")
            continue
    
    if not all_laps_list:
        log.warning("No lap section data found")
        return {}
    
    all_laps_df = pd.concat(all_laps_list, ignore_index=True)
    log.info(f"Total laps aggregated: {len(all_laps_df)}")
    
    # Step 2: Detect sections from CSV data (don't require track maps for now)
    # This allows best-case composites to be computed even without track map JSON files
    log.info("Detecting sections from CSV data instead of track maps...")
    
    # Step 3: Find fastest section times
    # Identify section columns (S1, S2, S3, etc.)
    section_cols = []
    for col in all_laps_df.columns:
        col_lower = col.lower().strip()
        if col_lower.startswith('s') and col_lower[1:].isdigit():
            section_cols.append(col)
    
    if not section_cols:
        log.warning("No section columns found in CSV")
        return {}
    
    log.info(f"Found section columns: {section_cols}")
    
    # Find lap/vehicle columns
    lap_col = None
    vehicle_col = None
    for col in all_laps_df.columns:
        col_lower = col.lower().strip()
        if col_lower == 'lap_number':
            lap_col = col
        elif 'vehicle' in col_lower or 'car' in col_lower or 'driver' in col_lower or col_lower == 'number':
            vehicle_col = col
    
    best_sections_info = {}
    
    # Map CSV section columns to simple section names
    # CSV uses S1, S2, etc. -> we'll use "Section 1", "Section 2", etc.
    section_name_map = {}
    for csv_col in section_cols:
        # Extract section number from column name (S1 -> 1, S2 -> 2, etc.)
        if csv_col.upper().startswith('S') and csv_col[1:].isdigit():
            section_num = int(csv_col[1:])
            section_name_map[csv_col] = f"Section {section_num}"
        else:
            # Fallback for unexpected column names
            section_name_map[csv_col] = csv_col
    
    # Find fastest time for each section
    for csv_col in section_cols:
        section_name = section_name_map.get(csv_col, csv_col)
        
        # Convert section times to milliseconds (CSV is in seconds)
        section_times = all_laps_df[csv_col].copy()

        # Convert to numeric, handling any non-numeric values
        section_times = pd.to_numeric(section_times, errors='coerce')

        # Convert seconds to milliseconds
        section_times_ms = section_times * 1000

        # Filter out NaN values and find minimum (fastest) time
        valid_times = section_times_ms.dropna()
        if valid_times.empty:
            log.warning(f"No valid times found for section {csv_col}")
            continue

        best_idx = valid_times.idxmin()
        best_row = all_laps_df.loc[best_idx]
        
        best_time_ms = float(section_times_ms.loc[best_idx])
        best_race_id = int(best_row['race_id'])
        best_lap_num = int(best_row[lap_col]) if lap_col else None
        
        best_sections_info[section_name] = {
            "best_time_ms": best_time_ms,
            "race_id": best_race_id,
            "lap_number": best_lap_num,
            "csv_section_col": csv_col,
        }
        
        log.info(f"Best {section_name}: {best_time_ms/1000:.3f}s from race {best_race_id}, lap {best_lap_num}")
    
    # Step 4: Create basic composite data (skip detailed telemetry extraction for now)
    # This provides the essential data needed for section analysis comparisons
    best_case_composites = {}
    
    for section_name, info in best_sections_info.items():
        # Create basic composite data - detailed telemetry extraction requires track maps
        best_case_composites[section_name] = {
            "best_time_ms": info['best_time_ms'],
            "source_race_id": info['race_id'],
            "source_lap_number": info['lap_number'],
            "optimal_telemetry_profile": {}  # Empty for now, can be enhanced later with track maps
        }
        log.info(f"Created composite for {section_name}: {info['best_time_ms']/1000:.3f}s from race {info['race_id']}, lap {info['lap_number']}")
    
    return best_case_composites

def save_composite_to_firestore(
    track_id: int,
    race_id: int = None,
    composites: Dict = None
):
    """Save best-case composite to Firestore."""
    db = get_firestore_client()
    collection_ref = db.collection("best_case_composites")
    
    log.info(f"Saving composite to Firestore: track_id={track_id}, race_id={race_id}")
    
    # Deactivate old composites
    query = collection_ref.where("track_id", "==", track_id).where("is_active", "==", True)
    if race_id is not None:
        query = query.where("race_id", "==", race_id)
    else:
        query = query.where("race_id", "==", None)
    
    for old_doc in query.stream():
        old_doc.reference.update({"is_active": False})
    
    # Save new composites
    saved_count = 0
    for section_name, data in composites.items():
        doc_id = f"track_{track_id}_{'race_' + str(race_id) + '_' if race_id else ''}section_{section_name}"
        
        composite_doc = {
            "track_id": track_id,
            "race_id": race_id,
            "section_name": section_name,
            "best_time_ms": data["best_time_ms"],
            "source_lap_id": data.get("source_lap_id") or data.get("source_race_id"),
            "optimal_telemetry_profile": data.get("optimal_telemetry_profile", {}),
            "analysis_version": "v1.0",
            "is_active": True,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        
        collection_ref.document(doc_id).set(composite_doc, merge=True)
        saved_count += 1
    
    log.info(f"Saved {saved_count} composite sections to Firestore")
    return saved_count

def compute_all_composites():
    """Compute best-case composites for all tracks and races from Firestore."""
    db = get_firestore_client()
    
    # Get all tracks
    tracks_ref = db.collection("tracks")
    tracks = list(tracks_ref.stream())
    log.info(f"Found {len(tracks)} tracks")
    
    # Compute per-track composites
    log.info("\n=== Computing Per-Track Best-Case Composites ===")
    for track_doc in tracks:
        track_data = track_doc.to_dict()
        track_id = track_data.get("id") or int(track_doc.id)
        track_name = track_data.get("name", "Unknown")
        
        log.info(f"\nComputing for track: {track_name} (ID: {track_id})")
        try:
            composites = compute_composite_from_gcs(track_id=track_id)
            if composites:
                saved = save_composite_to_firestore(track_id=track_id, race_id=None, composites=composites)
                log.info(f"  ✓ Created {saved} composite sections")
            else:
                log.warning(f"  ⚠ No lap sections found for track {track_id}")
        except Exception as e:
            log.error(f"  ✗ Error: {e}", exc_info=True)
    
    # Compute per-race composites
    log.info("\n=== Computing Per-Race Best-Case Composites ===")
    races_ref = db.collection("races")
    races = list(races_ref.stream())
    log.info(f"Found {len(races)} races")
    
    for race_doc in races:
        race_data = race_doc.to_dict()
        race_id = race_data.get("id") or int(race_doc.id)
        track_id = race_data.get("track_id")
        race_number = race_data.get("race_number", "?")
        
        log.info(f"\nComputing for race: {race_id} (Track: {track_id}, Race #{race_number})")
        try:
            composites = compute_composite_from_gcs(track_id=track_id, race_id=race_id)
            if composites:
                saved = save_composite_to_firestore(track_id=track_id, race_id=race_id, composites=composites)
                log.info(f"  ✓ Created {saved} composite sections")
            else:
                log.warning(f"  ⚠ No lap sections found for race {race_id}")
        except Exception as e:
            log.error(f"  ✗ Error: {e}", exc_info=True)

if __name__ == "__main__":
    compute_all_composites()

