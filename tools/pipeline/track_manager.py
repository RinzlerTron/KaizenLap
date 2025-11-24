"""
Track data management for KaizenLap ML Pipeline.

Purpose:
    Loads and manages track-specific data, including:
    - Track map JSON files
    - Section definitions
    - Section boundary distances (from distance measurements)

Status:
    ✅ New component to support accurate Section Analysis
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

INCHES_TO_METERS = 0.0254

log = logging.getLogger(__name__)


class Track:
    """
    Represents a single race track and its associated data.
    
    Loads section boundary information from track map JSON files.
    """
    
    _track_cache: Dict[str, 'Track'] = {}
    
    def __init__(self, track_name: str, track_map_data: Dict):
        """
        Initialize a Track object.
        
        Args:
            track_name: Name of the track (e.g., "barber")
            track_map_data: Loaded track map JSON data
        """
        self.track_name = track_name
        self.map_data = track_map_data
        self.sections: List[Dict] = []
        self._initialize_sections()

    def _initialize_sections(self):
        """
        Initializes section data with boundary distances.
        """
        distance_table = None
        for table in self.map_data.get("tables", []):
            if table.get("type") == "distance_measurements":
                distance_table = table
                break
        
        if not distance_table:
            log.warning(f"No distance measurements found for track {self.track_name}")
            return
        
        # Extract section distances
        section_distances = {}
        for row in distance_table.get("rows", []):
            measurement, inches = row
            if "Sector" in measurement:
                sector_name = measurement.split(" ")[1]
                try:
                    section_distances[sector_name] = float(inches) * INCHES_TO_METERS
                except (ValueError, TypeError):
                    log.warning(f"Invalid distance for {sector_name}: {inches}")
        
        # Calculate cumulative distances to define boundaries
        start_dist = 0.0
        
        # Sort sections by name (S1, S2, S3...)
        # A more robust implementation would use section_order if available
        sorted_section_names = sorted(section_distances.keys())
        
        for section_name in sorted_section_names:
            length_m = section_distances[section_name]
            end_dist = start_dist + length_m
            
            self.sections.append({
                "name": section_name,
                "start_distance_m": start_dist,
                "end_distance_m": end_dist,
                "length_m": length_m
            })
            
            start_dist = end_dist
            
        log.info(f"Initialized {len(self.sections)} sections for {self.track_name} with distance boundaries.")

    @classmethod
    def from_name(cls, track_name: str) -> Optional['Track']:
        """
        Load a Track object by name.
        
        Uses a cache to avoid reloading files.
        
        Args:
            track_name: Name of the track (e.g., "barber")
            
        Returns:
            Track object or None if not found
        """
        track_name = track_name.lower()
        
        if track_name in cls._track_cache:
            return cls._track_cache[track_name]
        
        # Construct path to track map JSON
        track_map_path = (
            Path(__file__).parent.parent.parent
            / "local" / "data" / "cloud_upload" / "processed" / "track_maps"
            / f"{track_name}_track_map.json"
        )
        
        if not track_map_path.exists():
            # Handle variations in naming (e.g., road-america)
            track_map_path = (
                Path(__file__).parent.parent.parent
                / "local" / "data" / "cloud_upload" / "processed" / "track_maps"
                / f"{track_name.replace('-', '_')}_track_map.json"
            )
            if not track_map_path.exists():
                log.error(f"Track map not found for {track_name} at {track_map_path}")
                return None
        
        try:
            with open(track_map_path, 'r') as f:
                track_data = json.load(f)
            
            track_obj = cls(track_name, track_data)
            cls._track_cache[track_name] = track_obj
            return track_obj
        
        except (json.JSONDecodeError, IOError) as e:
            log.error(f"Error loading track map for {track_name}: {e}")
            return None

    def get_section_boundaries(self) -> List[Dict]:
        """
        Return list of section boundaries.
        
        Returns:
            List of {"name": str, "start_distance_m": float, "end_distance_m": float}
        """
        return self.sections

    @property
    def total_distance_m(self) -> float:
        """
        Return total circuit length in meters.
        """
        if not self.sections:
            return 0.0
        return self.sections[-1]["end_distance_m"]














