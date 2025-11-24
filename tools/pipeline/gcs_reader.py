"""
Reads CSV files directly from GCS for ML pipeline.

Why: Avoids intermediate Firestore ingestion of large CSV files.
Note: Strips leading spaces from column names (CSV formatting quirk).
"""

import logging
from functools import lru_cache
from typing import Dict, Optional

import pandas as pd
from app.config import settings

log = logging.getLogger(__name__)

# Configuration - uses environment variables for judge's GCP project
import os
GCS_BUCKET_BASE_PATH = f"gs://{os.getenv('GCS_BUCKET', 'kaizenlap-data')}/primary/extracted"
LAP_SECTIONS_TEMPLATE = "23_AnalysisEnduranceWithSections_Race {race_num}_Anonymized.CSV"
WEATHER_TEMPLATE = "26_Weather_Race {race_num}_Anonymized.CSV"

# Import unified track name utility
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))
from app.utils.track_names import normalize_to_folder_name


def _get_track_folder_name(track_name: str) -> str:
    """
    Maps track name/abbreviation to GCS folder name.
    
    Uses unified track name utility for consistency.
    
    Args:
        track_name: Track name or abbreviation (e.g., "barber", "indy", "vir")
    
    Returns:
        Folder name as it appears in GCS (e.g., "indianapolis", "virginia-international-raceway")
    """
    return normalize_to_folder_name(track_name)


def construct_gcs_path(track_name: str, race_number: int, file_type: str) -> str:
    """
    Constructs the full GCS path for a given track, race number, and file type.

    Args:
        track_name: Track name or abbreviation (e.g., "barber", "indy")
        race_number: Race number (1 or 2)
        file_type: Type of file, either 'sections' or 'weather'

    Returns:
        The full gs:// path to the CSV file
    """
    track_folder = _get_track_folder_name(track_name)

    if file_type == 'sections':
        filename = LAP_SECTIONS_TEMPLATE.format(race_num=race_number)
    elif file_type == 'weather':
        filename = WEATHER_TEMPLATE.format(race_num=race_number)
    else:
        raise ValueError(f"Unknown file_type: {file_type}. Must be 'sections' or 'weather'")

    # Include Race X/ subdirectory in the path
    path = f"{GCS_BUCKET_BASE_PATH}/{track_folder}/Race {race_number}/{filename}"
    log.info(f"Constructed GCS path: {path}")
    return path


@lru_cache(maxsize=32)
def load_lap_sections_from_gcs(track_name: str, race_number: int) -> pd.DataFrame:
    """
    Reads lap sections data for a given race directly from a GCS CSV file.
    
    Uses LRU cache to avoid re-reading the same file multiple times.
    
    Args:
        track_name: Track name or abbreviation
        race_number: Race number (1 or 2)
    
    Returns:
        DataFrame with lap sections data
    
    Raises:
        FileNotFoundError: If file doesn't exist in GCS
        Exception: Other errors during reading/parsing
    """
    gcs_path = construct_gcs_path(track_name, race_number, 'sections')
    log.info(f"Attempting to read lap sections from {gcs_path}")

    try:
        # gcsfs is used automatically by pandas when the path starts with gs://
        # Read all columns first, then we'll filter/transform as needed
        # Note: These CSV files use semicolons as separators, not commas
        df = pd.read_csv(gcs_path, sep=';', low_memory=False)
        
        # Strip leading/trailing spaces from column names (CSV formatting issue)
        df.columns = df.columns.str.strip()
        
        log.info(f"Successfully loaded {len(df)} rows from {gcs_path}")
        log.info(f"Columns found: {list(df.columns)}")
        return df
    except FileNotFoundError as e:
        log.warning(f"File not found in GCS: {gcs_path}. Trying local data...")

        # Try to read from local data as fallback
        try:
            track_folder = _get_track_folder_name(track_name)
            local_path = f"local/data/cloud_upload/primary/extracted/{track_folder}/Race {race_number}/23_AnalysisEnduranceWithSections_Race {race_number}_Anonymized.CSV"
            df = pd.read_csv(local_path, sep=';', low_memory=False)
            log.info(f"Successfully loaded {len(df)} rows from local file {local_path}")
            log.info(f"Columns found: {list(df.columns)}")
            return df
        except FileNotFoundError:
            log.error(f"File not found locally either: {local_path}")
            raise
        except Exception as e:
            log.error(f"Failed to read local file {local_path}: {e}")
            raise
    except Exception as e:
        log.error(f"Failed to read or parse GCS file {gcs_path}: {e}")
        raise


@lru_cache(maxsize=32)
def load_weather_from_gcs(track_name: str, race_number: int) -> pd.DataFrame:
    """
    Reads weather data for a given race directly from a GCS CSV file.
    
    Handles multiple naming patterns found in GCS (same as lap sections).
    
    Uses LRU cache to avoid re-reading the same file multiple times.
    
    Args:
        track_name: Track name or abbreviation
        race_number: Race number (1 or 2)
    
    Returns:
        DataFrame with weather data
    
    Raises:
        FileNotFoundError: If file doesn't exist in GCS with any naming pattern
        Exception: Other errors during reading/parsing
    """
    gcs_path = construct_gcs_path(track_name, race_number, 'weather')
    log.info(f"Attempting to read weather data from {gcs_path}")
    
    try:
        # gcsfs is used automatically by pandas when the path starts with gs://
        # Weather CSV files use semicolons as separators, not commas
        df = pd.read_csv(gcs_path, sep=';', low_memory=False)
        
        # Strip leading/trailing spaces from column names (CSV formatting issue)
        df.columns = df.columns.str.strip()
        
        log.info(f"Successfully loaded {len(df)} rows from {gcs_path}")
        log.info(f"Columns found: {list(df.columns)}")
        return df
    except FileNotFoundError as e:
        log.error(f"File not found in GCS: {gcs_path}")
        raise
    except Exception as e:
        log.error(f"Failed to read or parse GCS file {gcs_path}: {e}")
        raise


def get_race_info_from_firestore(race_id: int, firestore_client) -> Optional[Dict]:
    """
    Gets race information (track_name, race_number) from Firestore.
    
    Args:
        race_id: Race identifier
        firestore_client: Firestore client instance
    
    Returns:
        Dictionary with 'track_name' and 'race_number', or None if not found
    """
    try:
        db = firestore_client
        race_ref = db.collection("races").document(str(race_id))
        race_doc = race_ref.get()
        
        if not race_doc.exists:
            # Try querying by id field
            race_query = db.collection("races").where("id", "==", race_id).limit(1)
            race_docs = list(race_query.stream())
            if not race_docs:
                log.warning(f"Race {race_id} not found in Firestore")
                return None
            race_data = race_docs[0].to_dict()
        else:
            race_data = race_doc.to_dict()
        
        track_id = race_data.get("track_id")
        race_number = race_data.get("race_number")
        
        if not track_id:
            log.warning(f"No track_id found for race {race_id}")
            return None
        
        # Get track abbreviation from Firestore
        track_ref = db.collection("tracks").document(str(track_id))
        track_doc = track_ref.get()
        
        if not track_doc.exists:
            track_query = db.collection("tracks").where("id", "==", track_id).limit(1)
            track_docs = list(track_query.stream())
            if not track_docs:
                log.warning(f"Track {track_id} not found in Firestore")
                return None
            track_data = track_docs[0].to_dict()
        else:
            track_data = track_doc.to_dict()
        
        track_name = track_data.get("abbreviation") or track_data.get("name", "").lower()
        
        return {
            "track_name": track_name,
            "race_number": race_number or 1,  # Default to 1 if not specified
        }
    except Exception as e:
        log.error(f"Error getting race info from Firestore: {e}")
        return None

