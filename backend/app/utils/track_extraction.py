"""
Utility functions for extracting track path from telemetry data.

Converts GPS coordinates from telemetry into track visualization data.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any
from pathlib import Path


def extract_track_path_from_telemetry(telemetry_file: str) -> List[Tuple[float, float]]:
    """
    Extract unique track path from telemetry GPS coordinates.
    
    Args:
        telemetry_file: Path to telemetry CSV file
    
    Returns:
        List of (latitude, longitude) tuples representing track outline
    """
    # Load telemetry data
    df = pd.read_csv(telemetry_file)
    
    # Extract GPS coordinates (assuming columns exist)
    # Note: Need to verify actual column names from data
    if 'latitude' in df.columns and 'longitude' in df.columns:
        coords = df[['latitude', 'longitude']].drop_duplicates()
    elif 'lat' in df.columns and 'lon' in df.columns:
        coords = df[['lat', 'lon']].drop_duplicates()
    else:
        # Try to identify GPS columns
        coords = _identify_gps_columns(df)
    
    # Smooth path (remove noise)
    track_path = _smooth_path(coords.values.tolist())
    
    return track_path


def _identify_gps_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify GPS coordinate columns in telemetry data.
    
    Args:
        df: Telemetry DataFrame
    
    Returns:
        DataFrame with latitude and longitude columns
    """
    # Look for common GPS column patterns
    lat_cols = [col for col in df.columns if 'lat' in col.lower()]
    lon_cols = [col for col in df.columns if 'lon' in col.lower() or 'lng' in col.lower()]
    
    if lat_cols and lon_cols:
        return df[[lat_cols[0], lon_cols[0]]]
    
    # If not found, return empty (will need manual mapping)
    return pd.DataFrame()


def _smooth_path(coords: List[Tuple[float, float]], window_size: int = 5) -> List[Tuple[float, float]]:
    """
    Smooth GPS path to remove noise.
    
    Args:
        coords: List of (lat, lon) coordinates
        window_size: Smoothing window size
    
    Returns:
        Smoothed coordinate list
    """
    if len(coords) < window_size:
        return coords
    
    coords_array = np.array(coords)
    smoothed = []
    
    for i in range(len(coords)):
        start = max(0, i - window_size // 2)
        end = min(len(coords), i + window_size // 2 + 1)
        window = coords_array[start:end]
        avg = np.mean(window, axis=0)
        smoothed.append((float(avg[0]), float(avg[1])))
    
    return smoothed


def map_sections_to_coordinates(
    lap_sections: List[Dict[str, Any]],
    telemetry_df: pd.DataFrame
) -> Dict[str, Dict[str, Tuple[float, float]]]:
    """
    Map section boundaries to GPS coordinates using telemetry timestamps.
    
    Args:
        lap_sections: List of section data with timestamps
        telemetry_df: Telemetry DataFrame with GPS and timestamps
    
    Returns:
        Dictionary mapping section names to start/end coordinates
    """
    section_coords = {}
    
    for section in lap_sections:
        section_name = section['section_name']
        start_time = section.get('start_timestamp')
        end_time = section.get('end_timestamp')
        
        if start_time and end_time:
            # Find GPS coordinates for section boundaries
            start_coords = _find_coords_at_timestamp(telemetry_df, start_time)
            end_coords = _find_coords_at_timestamp(telemetry_df, end_time)
            
            section_coords[section_name] = {
                "start": start_coords,
                "end": end_coords
            }
    
    return section_coords


def _find_coords_at_timestamp(
    df: pd.DataFrame,
    timestamp: Any
) -> Tuple[float, float]:
    """
    Find GPS coordinates at specific timestamp.
    
    Args:
        df: Telemetry DataFrame
        timestamp: Target timestamp
    
    Returns:
        (latitude, longitude) tuple
    """
    # Find closest timestamp in dataframe
    # Implementation depends on timestamp format
    # Return coordinates or default
    return (0.0, 0.0)  # Placeholder


def create_svg_path_from_coordinates(coords: List[Tuple[float, float]]) -> str:
    """
    Create SVG path string from GPS coordinates.
    
    Args:
        coords: List of (lat, lon) coordinates
    
    Returns:
        SVG path string (d attribute)
    """
    if not coords:
        return ""
    
    # Normalize coordinates to SVG space
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Scale to SVG coordinates (0-1000 range)
    svg_coords = []
    for lat, lon in coords:
        x = ((lon - min_lon) / (max_lon - min_lon)) * 1000 if max_lon != min_lon else 500
        y = ((lat - min_lat) / (max_lat - min_lat)) * 1000 if max_lat != min_lat else 500
        svg_coords.append((x, y))
    
    # Create SVG path
    path_parts = [f"M {svg_coords[0][0]} {svg_coords[0][1]}"]
    for x, y in svg_coords[1:]:
        path_parts.append(f"L {x} {y}")
    
    return " ".join(path_parts)

