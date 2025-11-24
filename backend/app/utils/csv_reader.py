"""
Read CSV files from GCS for drivers and laps data.
Simpler than querying nested Firestore documents.
"""

import logging
from functools import lru_cache
from typing import List, Dict, Optional
import pandas as pd
from google.cloud import storage
from app.config import settings
from app.utils.track_names import normalize_to_folder_name

log = logging.getLogger(__name__)


def _get_gcs_path(track_name: str, race_number: int, filename: str) -> str:
    """Construct GCS path for CSV file."""
    track_folder = normalize_to_folder_name(track_name)
    return f"primary/extracted/{track_folder}/Race {race_number}/{filename}"


@lru_cache(maxsize=32)
def _read_csv_from_gcs(gcs_path: str, sep: str = ';') -> Optional[pd.DataFrame]:
    """Read CSV file from GCS with caching."""
    try:
        storage_client = storage.Client(project=settings.PROJECT_ID)
        bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        
        if not blob.exists():
            log.warning(f"CSV file not found: {gcs_path}")
            return None
        
        # Download and read CSV (sections CSV uses semicolons)
        content = blob.download_as_text()
        df = pd.read_csv(pd.io.common.StringIO(content), sep=sep, low_memory=False)
        
        # Strip leading/trailing spaces from column names (CSV formatting quirk)
        df.columns = df.columns.str.strip()
        
        log.info(f"Loaded {len(df)} rows from {gcs_path}")
        return df
    except Exception as e:
        log.error(f"Error reading CSV from GCS {gcs_path}: {e}")
        return None


def get_drivers_from_csv(track_name: str, race_number: int) -> List[Dict]:
    """
    Get drivers from sections CSV file (23_AnalysisEnduranceWithSections).
    
    Uses NUMBER column which matches Firestore vehicle_id (no mapping needed).
    """
    filename = f"23_AnalysisEnduranceWithSections_Race {race_number}_Anonymized.CSV"
    gcs_path = _get_gcs_path(track_name, race_number, filename)
    df = _read_csv_from_gcs(gcs_path)
    
    if df is None or df.empty:
        return []
    
    # Get unique drivers from NUMBER column (this IS the vehicle_id used in Firestore)
    drivers = []
    if 'NUMBER' in df.columns:
        unique_numbers = df['NUMBER'].drop_duplicates()
        for vehicle_id in unique_numbers:
            if pd.notna(vehicle_id):
                drivers.append({
                    'id': int(vehicle_id),  # NUMBER column is the vehicle_id
                    'vehicle_id': int(vehicle_id),
                    'car_number': str(int(vehicle_id)),  # Use NUMBER as display
                })
    
    log.info(f"Found {len(drivers)} drivers from CSV")
    return sorted(drivers, key=lambda x: x['vehicle_id'])


def get_laps_from_csv(track_name: str, race_number: int, vehicle_id: int) -> List[Dict]:
    """
    Get laps for a driver from sections CSV file (23_AnalysisEnduranceWithSections).
    
    Uses NUMBER column (vehicle_id) and LAP_NUMBER column.
    Parses LAP_TIME to milliseconds.
    """
    filename = f"23_AnalysisEnduranceWithSections_Race {race_number}_Anonymized.CSV"
    gcs_path = _get_gcs_path(track_name, race_number, filename)
    df = _read_csv_from_gcs(gcs_path)
    
    if df is None or df.empty:
        return []
    
    # Filter by NUMBER (vehicle_id)
    driver_laps = df[df['NUMBER'] == vehicle_id].copy()
    
    if driver_laps.empty:
        return []
    
    # Find lap number and lap time columns (may have leading spaces)
    lap_num_col = None
    lap_time_col = None
    for col in df.columns:
        col_upper = col.upper().strip()
        if 'LAP_NUMBER' in col_upper or col_upper == 'LAP_NUMBER':
            lap_num_col = col
        if 'LAP_TIME' in col_upper and 'IMPROVEMENT' not in col_upper:
            lap_time_col = col
    
    if not lap_num_col or not lap_time_col:
        log.warning(f"Could not find lap number or lap time columns in CSV")
        return []
    
    # Parse lap times and group by lap number
    laps = []
    for lap_num in sorted(driver_laps[lap_num_col].unique()):
        lap_data = driver_laps[driver_laps[lap_num_col] == lap_num].iloc[0]
        
        # Parse LAP_TIME (format: "1:39.284" = 1 min 39.284 sec)
        lap_time_str = lap_data.get(lap_time_col, '')
        lap_time_ms = None
        
        if pd.notna(lap_time_str) and lap_time_str:
            try:
                # Parse "M:SS.mmm" format
                parts = str(lap_time_str).split(':')
                if len(parts) == 2:
                    minutes = float(parts[0])
                    seconds = float(parts[1])
                    total_seconds = minutes * 60 + seconds
                    lap_time_ms = int(total_seconds * 1000)
            except (ValueError, IndexError):
                pass
        
        if lap_time_ms is None:
            continue  # Skip if we can't parse time
        
        laps.append({
            'id': f"{race_number}|{vehicle_id}|{int(lap_num)}",  # Composite key
            'lap_number': int(lap_num),
            'lap_time_ms': lap_time_ms,
            'is_valid': True
        })
    
    log.info(f"Found {len(laps)} laps for vehicle {vehicle_id}")
    return sorted(laps, key=lambda x: x['lap_number'])

