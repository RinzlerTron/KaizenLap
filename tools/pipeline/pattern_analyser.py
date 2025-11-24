"""
Pattern Analyser for KaizenLap ML Pipeline.

Purpose:
    Analyzes driver consistency across multiple laps, identifies patterns and trends,
    detects strengths and weaknesses per section, and generates insights.

Status:
    ✅ Enhanced version with GCS/Firestore integration
    Reads race data from Firestore/PostgreSQL, analyzes patterns, saves recommendations to Firestore

Input:
    - Race ID (to fetch race data from Firestore/PostgreSQL)
    - Lap timing data
    - Section timing data (optional, for section-by-section analysis)

Output:
    - Structured analysis with consistency metrics, trends, and pattern insights
    - Saved to Firestore `ml_pattern_recommendations` collection

Dependencies:
    - Race data with lap timing from database/Firestore
    - Section timing data (optional)
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add backend to path for imports
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import pandas as pd
import numpy as np
from app.config import settings
from base_analyser import BaseAnalyser
import ml_config
from ml_config import *
from gcs_reader import load_lap_sections_from_gcs, get_race_info_from_firestore

# Google Cloud imports
try:
    from google.cloud import firestore
    from google.auth.exceptions import DefaultCredentialsError
except ImportError:
    firestore = None
    DefaultCredentialsError = Exception

log = logging.getLogger(__name__)


class PatternAnalyser(BaseAnalyser):
    """
    Analyzes driver consistency and patterns.
    
    Enhanced version that:
    - Loads race data from Firestore/PostgreSQL
    - Analyzes consistency across laps
    - Identifies trends and patterns
    - Detects strengths/weaknesses per section
    - Generates structured insights
    - Saves results to Firestore
    """
    
    def __init__(self, race_id: int, vehicle_id: Optional[int] = None,
                 firestore_client: Optional[firestore.Client] = None):
        """
        Initialize Pattern Analyser.
        
        Args:
            race_id: Race identifier
            vehicle_id: Optional vehicle/driver identifier (if None, analyzes all vehicles)
            firestore_client: Optional Firestore client (will create if not provided)
        """
        super().__init__(race_id, firestore_client)
        self.vehicle_id = vehicle_id
        self.race_data: Optional[Dict] = None
        
    def _load_race_data(self) -> Dict:
        """
        Load race data (laps, sections, etc.) from CSV files and Firestore metadata.
        """
        log.info(f"Loading race data for race {self.race_id}...")

        # Get race metadata from Firestore
        db = self._get_firestore_client()
        race_ref = db.collection("races").document(str(self.race_id))
        race_doc = race_ref.get()

        if not race_doc.exists:
            race_ref = db.collection("races").where("id", "==", self.race_id).limit(1)
            race_docs = list(race_ref.stream())
            if not race_docs:
                raise ValueError(f"Race {self.race_id} not found in Firestore.")
            race_doc = race_docs[0]

        race_data = race_doc.to_dict()
        track_id = race_data.get("track_id")

        # Get race_number for CSV loading
        race_number = race_data.get('race_number', 1)

        # Get track name from track_id
        track_ref = db.collection("tracks").document(str(track_id))
        track_doc = track_ref.get()
        if track_doc.exists:
            track_data = track_doc.to_dict()
            track_name = track_data.get("abbreviation", "barber")  # fallback to barber
        else:
            track_name = "barber"  # fallback

        # Load lap data from CSV files (same approach as section analyser)
        try:
            from gcs_reader import load_lap_sections_from_gcs
            lap_sections_df = load_lap_sections_from_gcs(track_name, race_number)
        except Exception as e:
            log.error(f"Failed to load lap sections data: {e}")
            return {"race_id": self.race_id, "laps_data": []}

        # Convert CSV data to lap format expected by analyser
        laps_data = []
        if not lap_sections_df.empty:
            vehicles = lap_sections_df['NUMBER'].unique()

            for vehicle_id in vehicles:
                vehicle_data = lap_sections_df[lap_sections_df['NUMBER'] == vehicle_id]
                vehicle_laps = vehicle_data[' LAP_NUMBER'].unique()

                for lap_num in vehicle_laps:
                    lap_data = vehicle_data[vehicle_data[' LAP_NUMBER'] == lap_num]

                    if lap_data.empty:
                        continue

                    # Calculate total lap time from sections
                    section_cols = [col for col in lap_data.columns if col.strip().startswith('S') and col.strip()[1:].isdigit()]
                    total_time = 0
                    for col in section_cols:
                        time_val = lap_data[col].iloc[0]
                        if pd.notna(time_val):
                            try:
                                # Handle time strings like "1:00.255"
                                if isinstance(time_val, str) and ':' in time_val:
                                    # Convert MM:SS.mmm to seconds
                                    parts = time_val.split(':')
                                    if len(parts) == 2:
                                        minutes = float(parts[0])
                                        seconds = float(parts[1])
                                        total_time += minutes * 60 + seconds
                                    else:
                                        total_time += float(time_val)
                                else:
                                    total_time += float(time_val)
                            except (ValueError, TypeError):
                                pass

                    laps_data.append({
                        "lap_id": f"{vehicle_id}_{lap_num}",
                        "lap_number": int(lap_num),
                        "lap_time_ms": total_time * 1000,  # Store as milliseconds as expected by analyser
                        "vehicle_id": int(vehicle_id),
                    })

        log.info(f"Loaded race data from CSV: {len(laps_data)} laps")

        return {
            "race_id": self.race_id,
            "track_id": track_id,
            "laps_data": laps_data,
        }
    
    def _parse_lap_sections_csv(self, sections_df: pd.DataFrame) -> Dict:
        """
        Parse lap sections CSV DataFrame into the expected race_data format.
        
        Args:
            sections_df: DataFrame from 23_AnalysisEnduranceWithSections CSV
        
        Returns:
            Dictionary with 'laps_data' list containing lap and section information
        """
        if sections_df.empty:
            return {"race_id": self.race_id, "laps_data": []}
        
        # Identify column names (may vary by track)
        # Common columns: Lap, Driver, Car, LapTime, s1, s2, s3, etc.
        lap_col = None
        vehicle_col = None
        lap_time_col = None
        
        # Find lap column
        for col in sections_df.columns:
            col_lower = col.lower()
            if 'lap' in col_lower and 'time' not in col_lower:
                lap_col = col
            elif 'lap' in col_lower and 'time' in col_lower:
                lap_time_col = col
            elif 'vehicle' in col_lower or 'car' in col_lower or 'driver' in col_lower:
                vehicle_col = col
        
        if not lap_col:
            log.warning("Could not find lap column in CSV. Available columns: " + str(list(sections_df.columns)))
            return {"race_id": self.race_id, "laps_data": []}
        
        # Find section columns (s1, s2, s3, etc. or Sector 1, Sector 2, etc.)
        section_cols = []
        for col in sections_df.columns:
            col_lower = col.lower().strip()
            if col_lower.startswith('s') and col_lower[1:].isdigit():
                section_cols.append(col)
            elif 'sector' in col_lower or 'section' in col_lower:
                section_cols.append(col)
        
        log.info(f"Found {len(section_cols)} section columns: {section_cols}")
        
        # Group by lap and vehicle
        laps_data = []
        grouped = sections_df.groupby([lap_col, vehicle_col] if vehicle_col else [lap_col])
        
        for (lap_num, vehicle_id), group_df in grouped:
            if vehicle_col:
                vehicle_id_value = vehicle_id
            else:
                vehicle_id_value = None
            
            # Get lap time
            lap_time_ms = None
            if lap_time_col and lap_time_col in group_df.columns:
                lap_time_value = group_df[lap_time_col].iloc[0]
                # Convert to milliseconds if needed
                if isinstance(lap_time_value, (int, float)):
                    # Assume seconds if < 1000, otherwise milliseconds
                    lap_time_ms = int(lap_time_value * 1000) if lap_time_value < 1000 else int(lap_time_value)
            
            # Extract section times
            sections_dict = {}
            for idx, section_col in enumerate(section_cols):
                section_time_value = group_df[section_col].iloc[0] if section_col in group_df.columns else None
                if pd.notna(section_time_value) and section_time_value is not None:
                    # Convert to milliseconds
                    section_time_ms = int(float(section_time_value) * 1000) if float(section_time_value) < 1000 else int(float(section_time_value))
                    section_name = f"Sector {idx + 1}"  # Default naming
                    sections_dict[section_name] = {
                        "section_id": None,  # Not available from CSV
                        "section_time_ms": section_time_ms,
                        "section_order": idx + 1,
                    }
            
            laps_data.append({
                "lap_id": None,  # Not available from CSV
                "lap_number": int(lap_num) if isinstance(lap_num, (int, float)) else None,
                "lap_time_ms": lap_time_ms,
                "vehicle_id": vehicle_id_value,
                "sections": sections_dict,
            })
        
        return {
            "race_id": self.race_id,
            "track_id": None,  # Will be set from Firestore if needed
            "laps_data": laps_data,
        }
    
    def _analyze_consistency(self, laps_df: pd.DataFrame) -> Dict:
        """
        Analyze driver consistency across laps.

        Returns:
            Dictionary with consistency metrics
        """
        if laps_df.empty or 'lap_time_s' not in laps_df.columns:
            return {}
        
        lap_times = laps_df['lap_time_s'].values
        
        # Find lap numbers for min/max times
        min_lap_idx = np.argmin(lap_times)
        max_lap_idx = np.argmax(lap_times)
        min_lap_number = None
        max_lap_number = None
        
        if 'lap_number' in laps_df.columns:
            min_lap_number = int(laps_df.iloc[min_lap_idx]['lap_number']) if min_lap_idx < len(laps_df) else None
            max_lap_number = int(laps_df.iloc[max_lap_idx]['lap_number']) if max_lap_idx < len(laps_df) else None
        
        consistency_metrics = {
            "mean_lap_time_s": float(np.mean(lap_times)),
            "std_lap_time_s": float(np.std(lap_times)),
            "min_lap_time_s": float(np.min(lap_times)),
            "max_lap_time_s": float(np.max(lap_times)),
            "min_lap_number": min_lap_number,
            "max_lap_number": max_lap_number,
            "lap_count": len(lap_times),
            "consistency_score": 0.0,  # Will calculate
            "improvement_trend": "stable"  # Will analyze
        }
        
        # Calculate consistency score (0-10, higher = more consistent)
        # Lower std deviation = higher consistency
        if consistency_metrics["std_lap_time_s"] > 0:
            # Normalize: std of 0.1s = score 10, std of 2.0s = score 0
            consistency_score = max(0, 10.0 - (consistency_metrics["std_lap_time_s"] * ml_config.pattern_scores["consistency_std_multiplier"]))
            consistency_metrics["consistency_score"] = float(consistency_score)
        
        # Analyze improvement trend
        if len(lap_times) >= ml_config.analysis_params["min_laps_for_pattern_trend"]:
            # Compare first half vs second half
            mid_point = len(lap_times) // 2
            first_half_mean = np.mean(lap_times[:mid_point])
            second_half_mean = np.mean(lap_times[mid_point:])
            
            if second_half_mean < first_half_mean + ml_config.pattern_scores["trend_improvement_threshold_s"]:  # Improved by >0.1s
                consistency_metrics["improvement_trend"] = "improving"
            elif second_half_mean > first_half_mean + ml_config.pattern_scores["trend_decline_threshold_s"]:  # Slowed by >0.1s
                consistency_metrics["improvement_trend"] = "declining"
            else:
                consistency_metrics["improvement_trend"] = "stable"
        
        return consistency_metrics
    
    def _analyze_section_patterns(self, race_data: Dict) -> Dict:
        """
        Analyze patterns per section.

        Args:
            race_data: Race data with lap sections

        Returns:
            Dictionary with section-by-section analysis
        """
        if not race_data.get('laps_data'):
            return {}
        
        # Collect section times per section
        section_times = {}
        
        for lap_info in race_data['laps_data']:
            for section_name, section_info in lap_info.get('sections', {}).items():
                if section_name not in section_times:
                    section_times[section_name] = []
                
                section_time_ms = section_info.get('section_time_ms')
                if section_time_ms:
                    section_times[section_name].append(section_time_ms / 1000.0)  # Convert to seconds
        
        # Analyze each section
        section_analysis = {}
        for section_name, times in section_times.items():
            if len(times) < 2:
                continue
            
            times_array = np.array(times)
            section_analysis[section_name] = {
                "mean_time_s": float(np.mean(times_array)),
                "std_time_s": float(np.std(times_array)),
                "min_time_s": float(np.min(times_array)),
                "max_time_s": float(np.max(times_array)),
                "consistency": "high" if np.std(times_array) < ml_config.pattern_scores["section_consistency_high_std"] else "moderate" if np.std(times_array) < ml_config.pattern_scores["section_consistency_moderate_std"] else "low"
            }
        
        # Identify strengths (consistent, fast sections) and weaknesses (inconsistent, slow sections)
        strengths = []
        weaknesses = []
        
        for section_name, analysis in section_analysis.items():
            consistency = analysis["consistency"]
            mean_time = analysis["mean_time_s"]
            
            # Strength: consistent and relatively fast
            if consistency == "high":
                strengths.append(section_name)
            # Weakness: inconsistent
            elif consistency == "low":
                weaknesses.append(section_name)
        
        return {
            "section_analysis": section_analysis,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "total_sections_analyzed": len(section_analysis)
        }
    
    def _save_recommendations_to_firestore(self, recommendations: List[Dict]):
        """Save pattern analysis recommendations to Firestore ml_pattern_recommendations collection."""
        if not recommendations:
            log.info("No recommendations to save.")
            return

        db = self._get_firestore_client()
        collection_ref = db.collection("ml_pattern_recommendations")

        log.info(f"Saving {len(recommendations)} pattern analysis recommendations to Firestore...")

        for rec in recommendations:
            # Create document ID
            vehicle_id = rec.get("vehicle_id", "all")
            doc_id = f"race_{rec['race_id']}_vehicle_{vehicle_id}_pattern_analysis"

            # Prepare Firestore document
            firestore_doc = {
                "race_id": rec["race_id"],
                "vehicle_id": rec.get("vehicle_id"),
                "recommendation_type": "driver_pattern",
                "consistency_analysis": rec.get("consistency_analysis", {}),
                "section_patterns": rec.get("section_patterns", {}),
                "trends": rec.get("trends", {}),
                "structured_data": rec,  # Full structured data
                "created_at": firestore.SERVER_TIMESTAMP,
            }

            collection_ref.document(doc_id).set(firestore_doc, merge=True)
            log.debug(f"Saved pattern analysis recommendation: {doc_id}")

        log.info(f"Successfully saved {len(recommendations)} pattern analysis recommendations to Firestore.")

    def run_analysis(self) -> List[Dict]:
        """
        Main analysis method.
        
        Loads data, analyzes patterns for each vehicle, and saves recommendations.
        """
        log.info("--- Starting Pattern Analysis ---")
        
        self.race_data = self._load_race_data()
        
        if not self.race_data or not self.race_data.get('laps_data'):
            log.warning(f"No lap data found for race {self.race_id}")
            return []
            
        full_laps_df = pd.DataFrame(self.race_data['laps_data'])
        
        if full_laps_df.empty or 'vehicle_id' not in full_laps_df.columns:
            log.warning("No lap data or vehicle_id available for analysis.")
            return []

        # Determine which vehicles to analyze
        if self.vehicle_id:
            vehicles_to_analyze = [self.vehicle_id]
        else:
            vehicles_to_analyze = full_laps_df['vehicle_id'].unique()
            log.info(f"No specific vehicle ID provided. Analyzing all {len(vehicles_to_analyze)} vehicles.")

        all_results = []

        for vehicle_id in vehicles_to_analyze:
            log.info(f"--- Analyzing patterns for Vehicle ID: {vehicle_id} ---")
            
            vehicle_laps_df = full_laps_df[full_laps_df['vehicle_id'] == vehicle_id].copy()
            
            if len(vehicle_laps_df) < 2:
                log.warning(f"Not enough laps for Vehicle {vehicle_id} to analyze patterns.")
                continue

            # Convert lap_time_ms to seconds
            if 'lap_time_ms' in vehicle_laps_df.columns:
                vehicle_laps_df['lap_time_s'] = vehicle_laps_df['lap_time_ms'] / 1000.0
            else:
                log.warning(f"Missing 'lap_time_ms' for Vehicle {vehicle_id}.")
                continue

            # Analyze consistency
            consistency_analysis = self._analyze_consistency(vehicle_laps_df)
            
            # Analyze section patterns for this vehicle's laps
            vehicle_race_data = {
                'laps_data': [
                    lap for lap in self.race_data['laps_data'] 
                    if lap.get('vehicle_id') == vehicle_id
                ]
            }
            section_patterns = self._analyze_section_patterns(vehicle_race_data)
            
            # Build trends summary
            trends = {
                "improvement_trend": consistency_analysis.get("improvement_trend", "stable"),
                "consistency_trend": "improving" if consistency_analysis.get("consistency_score", 0) > ml_config.pattern_scores["consistency_trend_improving_score"] else "needs_work",
                "lap_count": consistency_analysis.get("lap_count", 0)
            }
            
            result = {
                "type": "driver_pattern",
                "race_id": self.race_id,
                "vehicle_id": int(vehicle_id),
                "consistency_analysis": consistency_analysis,
                "section_patterns": section_patterns,
                "trends": trends,
            }
            all_results.append(result)

        log.info(f"--- Pattern Analysis Complete. Generated insights for {len(all_results)} vehicles. ---")
        
        # Save recommendations to Firestore
        if all_results:
            self._save_recommendations_to_firestore(all_results)
        
        return all_results




















