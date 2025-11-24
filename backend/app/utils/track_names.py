"""
Unified Track Name Utility for KaizenLap.

Single source of truth for track name mappings and normalization.
Used by all code to ensure consistent track name handling.
"""

from typing import Dict, Optional

# Track ID mapping (from database)
TRACK_IDS: Dict[str, int] = {
    "barber": 1,
    "cota": 2,
    "indianapolis": 3,
    "road-america": 4,
    "sebring": 5,
    "sonoma": 6,
    "virginia-international-raceway": 7,
}

# Track folder name mapping (abbreviation -> actual folder name in local/GCS)
# This maps what code uses to what folders are actually named
TRACK_FOLDER_MAP: Dict[str, str] = {
    # Standard names (folder names)
    "barber": "barber",
    "indianapolis": "indianapolis",
    "road-america": "road-america",
    "sebring": "sebring",
    "sonoma": "sonoma",
    "virginia-international-raceway": "virginia-international-raceway",
    "COTA": "COTA",  # Keep uppercase as folder is uppercase
    
    # Abbreviations -> folder names
    "indy": "indianapolis",
    "vir": "virginia-international-raceway",
    "cota": "COTA",  # lowercase abbreviation -> uppercase folder
    
    # Display names -> folder names
    "indianapolis motor speedway": "indianapolis",
    "virginia international raceway": "virginia-international-raceway",
    "circuit of the americas": "COTA",
}

# Track abbreviations (for API responses, display)
TRACK_ABBREVIATIONS: Dict[str, str] = {
    "barber": "barber",
    "indianapolis": "indy",
    "road-america": "road-america",
    "sebring": "sebring",
    "sonoma": "sonoma",
    "virginia-international-raceway": "vir",
    "COTA": "cota",
}


def normalize_to_folder_name(track_name: str) -> str:
    """
    Normalize any track name/abbreviation to the actual folder name.
    
    This is the function to use when constructing file paths or GCS paths.
    
    Args:
        track_name: Track name in any format (abbreviation, display name, etc.)
    
    Returns:
        Actual folder name as it appears in local/GCS directories
    
    Examples:
        normalize_to_folder_name("indy") -> "indianapolis"
        normalize_to_folder_name("vir") -> "virginia-international-raceway"
        normalize_to_folder_name("cota") -> "COTA"
        normalize_to_folder_name("barber") -> "barber"
    """
    if not track_name:
        raise ValueError("Track name cannot be empty")
    
    track_name_lower = track_name.lower().strip()
    
    # Direct mapping
    if track_name_lower in TRACK_FOLDER_MAP:
        return TRACK_FOLDER_MAP[track_name_lower]
    
    # Try partial match
    for key, folder_name in TRACK_FOLDER_MAP.items():
        if key.lower() in track_name_lower or track_name_lower in key.lower():
            return folder_name
    
    # If not found, return as-is (might be already correct)
    return track_name


def get_track_id(track_name: str) -> Optional[int]:
    """
    Get track ID from track name.
    
    Args:
        track_name: Track name in any format
    
    Returns:
        Track ID (1-7) or None if not found
    """
    folder_name = normalize_to_folder_name(track_name)
    return TRACK_IDS.get(folder_name.lower())


def get_track_abbreviation(track_name: str) -> str:
    """
    Get track abbreviation from track name.
    
    Args:
        track_name: Track name in any format
    
    Returns:
        Track abbreviation (e.g., "indy", "vir", "cota")
    """
    folder_name = normalize_to_folder_name(track_name)
    return TRACK_ABBREVIATIONS.get(folder_name, folder_name.lower())


def is_valid_track_name(track_name: str) -> bool:
    """
    Check if track name is valid.
    
    Args:
        track_name: Track name to validate
    
    Returns:
        True if track name is recognized, False otherwise
    """
    try:
        folder_name = normalize_to_folder_name(track_name)
        return folder_name.lower() in [name.lower() for name in TRACK_IDS.keys()]
    except (ValueError, KeyError):
        return False


# Convenience constants for common track names
BARBER = "barber"
COTA = "COTA"
INDIANAPOLIS = "indianapolis"
ROAD_AMERICA = "road-america"
SEBRING = "sebring"
SONOMA = "sonoma"
VIR = "virginia-international-raceway"

# Track ID constants
TRACK_ID_BARBER = 1
TRACK_ID_COTA = 2
TRACK_ID_INDIANAPOLIS = 3
TRACK_ID_ROAD_AMERICA = 4
TRACK_ID_SEBRING = 5
TRACK_ID_SONOMA = 6
TRACK_ID_VIR = 7






