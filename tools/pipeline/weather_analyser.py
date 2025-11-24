"""
Weather Impact Analyser for KaizenLap ML Pipeline.

Purpose:
    Analyzes correlation between weather conditions (air temp, track temp, humidity, wind)
    and performance metrics, identifies best performers in specific conditions, and
    generates insights on what they did differently.

Status:
    ✅ Enhanced version with GCS/Firestore integration
    Reads race data and weather data from Firestore/PostgreSQL, saves recommendations to Firestore

Input:
    - Race ID (to fetch race data and weather data from Firestore/PostgreSQL)
    - Weather data from database
    - Lap timing data from database

Output:
    - Structured analysis with weather correlations and best performer insights
    - Saved to Firestore `ml_weather_recommendations` collection

Dependencies:
    - Race data with weather information from database/Firestore
    - Lap timing data from database/Firestore
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
from ml_config import *
from gcs_reader import load_weather_from_gcs, get_race_info_from_firestore

# Google Cloud imports
try:
    from google.cloud import firestore
    from google.auth.exceptions import DefaultCredentialsError
except ImportError:
    firestore = None
    DefaultCredentialsError = Exception

log = logging.getLogger(__name__)


class WeatherImpactAnalyser(BaseAnalyser):
    """
    Analyzes weather impact on performance.
    
    Enhanced version that:
    - Loads race and weather data from Firestore/PostgreSQL
    - Calculates correlations between weather and performance
    - Identifies best performers in specific conditions
    - Generates structured insights
    - Saves results to Firestore
    """
    
    def __init__(self, race_id: int, firestore_client: Optional[firestore.Client] = None):
        """
        Initialize Weather Impact Analyser.
        
        Args:
            race_id: Race identifier
            firestore_client: Optional Firestore client (will create if not provided)
        """
        super().__init__(race_id, firestore_client)
        self.race_data: Optional[Dict] = None
        self.weather_data: Optional[List[Dict]] = None
        
    def _load_race_data(self) -> Dict:
        """
        Load race data (laps, timing) from CSV files and Firestore metadata.
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
            return {"race_id": self.race_id, "laps_data": [], "weather_data": []}

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
                                total_time += float(time_val)
                            except (ValueError, TypeError):
                                pass

                    laps_data.append({
                        "lap_id": f"{vehicle_id}_{lap_num}",
                        "lap_number": int(lap_num),
                        "lap_time_ms": total_time * 1000,  # Convert seconds to ms
                        "vehicle_id": int(vehicle_id),
                    })

        log.info(f"Loaded race data from CSV: {len(laps_data)} laps")

        return {
            "race_id": self.race_id,
            "track_id": track_id,
            "laps_data": laps_data,
            "weather_data": []  # Will load separately
        }
    
    def _load_weather_data(self) -> List[Dict]:
        """
        Load weather data from GCS CSV files first, then fallback to Firestore.
        
        ⚠️ PostgreSQL is LOCAL TESTING ONLY - not used in production.
        
        Returns list of weather data points.
        """
        log.info(f"Loading weather data for race {self.race_id}...")
        
        # 1. Try reading weather CSV directly from GCS
        try:
            log.info(f"Attempting to load weather data from GCS for race {self.race_id}")
            
            # Get race info (track_name, race_number) from Firestore
            db = self._get_firestore_client()
            race_info = get_race_info_from_firestore(self.race_id, db)
            
            if not race_info:
                raise ValueError(f"Could not get race info for race {self.race_id}")
            
            track_name = race_info.get("track_name")
            race_number = race_info.get("race_number", 1)
            
            if not track_name:
                raise ValueError(f"No track_name found for race {self.race_id}")
            
            # Read CSV from GCS
            weather_df = load_weather_from_gcs(track_name, race_number)
            
            # Parse CSV data into expected format
            weather_data = self._parse_weather_csv(weather_df)
            
            if weather_data:
                log.info(f"Loaded weather data from GCS: {len(weather_data)} records")
                return weather_data
                
        except Exception as e:
            log.warning(f"Could not load weather data from GCS for race {self.race_id}: {e}. Falling back to Firestore...")
        
        # 2. Fallback: Load from Firestore
        db = self._get_firestore_client()
        weather_ref = db.collection("weather_data")
        weather_query = weather_ref.where("race_id", "==", self.race_id)
        weather_docs = weather_query.stream()
        
        weather_data = []
        for wd_doc in weather_docs:
            wd_data = wd_doc.to_dict()
            weather_data.append({
                "timestamp": wd_data.get("timestamp"),
                "air_temp_celsius": wd_data.get("air_temp_celsius"),
                "track_temp_celsius": wd_data.get("track_temp_celsius"),
                "humidity_percent": wd_data.get("humidity_percent"),
                "wind_speed": wd_data.get("wind_speed"),
                "wind_direction_degrees": wd_data.get("wind_direction_degrees"),
                "rain_indicator": wd_data.get("rain_indicator")
            })
        
        log.info(f"Loaded weather data from Firestore: {len(weather_data)} records")
        return weather_data
    
    def _parse_weather_csv(self, weather_df: pd.DataFrame) -> List[Dict]:
        """
        Parse weather CSV DataFrame into the expected weather_data format.
        
        Args:
            weather_df: DataFrame from 26_Weather CSV
        
        Returns:
            List of dictionaries with weather data points
        """
        if weather_df.empty:
            return []
        
        # Identify column names (may vary by track)
        # Common columns: TIME_UTC_SECONDS, TIME_UTC_STR, AIR_TEMP, TRACK_TEMP, HUMIDITY, WIND_SPEED, etc.
        timestamp_col = None
        air_temp_col = None
        track_temp_col = None
        humidity_col = None
        wind_speed_col = None
        wind_dir_col = None
        rain_col = None
        
        for col in weather_df.columns:
            col_lower = col.lower().strip()
            if 'time' in col_lower or 'timestamp' in col_lower:
                timestamp_col = col
            elif 'air' in col_lower and 'temp' in col_lower:
                air_temp_col = col
            elif 'track' in col_lower and 'temp' in col_lower:
                track_temp_col = col
            elif 'humidity' in col_lower:
                humidity_col = col
            elif 'wind' in col_lower and 'speed' in col_lower:
                wind_speed_col = col
            elif 'wind' in col_lower and ('dir' in col_lower or 'direction' in col_lower):
                wind_dir_col = col
            elif 'rain' in col_lower:
                rain_col = col
        
        log.info(f"Weather CSV columns mapped: timestamp={timestamp_col}, air_temp={air_temp_col}, "
                 f"track_temp={track_temp_col}, humidity={humidity_col}, wind_speed={wind_speed_col}, rain={rain_col}")
        log.info(f"Available columns in weather CSV: {list(weather_df.columns)}")

        weather_data = []
        for _, row in weather_df.iterrows():
            weather_point = {}
            
            # Parse timestamp
            if timestamp_col and timestamp_col in row.index:
                timestamp_value = row[timestamp_col]
                if pd.notna(timestamp_value):
                    # Try to parse as datetime
                    try:
                        if isinstance(timestamp_value, str):
                            weather_point["timestamp"] = pd.to_datetime(timestamp_value).isoformat()
                        else:
                            weather_point["timestamp"] = pd.to_datetime(timestamp_value).isoformat()
                    except:
                        weather_point["timestamp"] = str(timestamp_value)
            
            # Parse temperatures
            if air_temp_col and air_temp_col in row.index:
                weather_point["air_temp_celsius"] = float(row[air_temp_col]) if pd.notna(row[air_temp_col]) else None
            if track_temp_col and track_temp_col in row.index:
                weather_point["track_temp_celsius"] = float(row[track_temp_col]) if pd.notna(row[track_temp_col]) else None
            
            # Parse humidity
            if humidity_col and humidity_col in row.index:
                weather_point["humidity_percent"] = float(row[humidity_col]) if pd.notna(row[humidity_col]) else None
            
            # Parse wind
            if wind_speed_col and wind_speed_col in row.index:
                weather_point["wind_speed"] = float(row[wind_speed_col]) if pd.notna(row[wind_speed_col]) else None
            if wind_dir_col and wind_dir_col in row.index:
                weather_point["wind_direction_degrees"] = float(row[wind_dir_col]) if pd.notna(row[wind_dir_col]) else None
            
            # Parse rain indicator
            if rain_col and rain_col in row.index:
                weather_point["rain_indicator"] = int(row[rain_col]) if pd.notna(row[rain_col]) else 0
            
            weather_data.append(weather_point)
        
        return weather_data
    
    def _calculate_weather_correlations(self, laps_df: pd.DataFrame, weather_df: pd.DataFrame) -> Dict:
        """
        Calculate correlations between weather conditions and lap times.
        
        Args:
            laps_df: DataFrame with lap timing data
            weather_df: DataFrame with weather data
            
        Returns:
            Dictionary with correlation analysis
        """
        if laps_df.empty:
            return {}
        
        # Convert lap_time_ms to seconds
        if 'lap_time_ms' in laps_df.columns:
            laps_df = laps_df.copy()
            laps_df['lap_time_s'] = laps_df['lap_time_ms'] / 1000.0
        
        if 'lap_time_s' not in laps_df.columns:
            log.warning("No lap time data available for correlation analysis.")
            return {}
        
        # --- IMPORTANT IMPROVEMENT ---
        # Original logic used a race-wide average. This version time-aligns weather
        # data to each lap for more accurate correlation.
        if not weather_df.empty and 'timestamp' in weather_df.columns and 'lap_start_time' in laps_df.columns:
            # Ensure data types are correct for merging
            weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'], errors='coerce')
            laps_df['lap_start_time'] = pd.to_datetime(laps_df['lap_start_time'], errors='coerce')

            weather_df = weather_df.sort_values('timestamp').dropna(subset=['timestamp'])
            laps_df = laps_df.sort_values('lap_start_time').dropna(subset=['lap_start_time'])

            # Merge weather data based on nearest timestamp
            laps_with_weather_df = pd.merge_asof(
                left=laps_df,
                right=weather_df,
                left_on='lap_start_time',
                right_on='timestamp',
                direction='nearest'
            )
        else:
            log.warning("Not enough data for time-aligned weather analysis. Providing basic weather summary instead.")
            # Provide basic weather summary when time-aligned analysis isn't possible
            return self._provide_basic_weather_summary(weather_df)
        
        # Calculate correlations
        weather_cols = ['air_temp_celsius', 'track_temp_celsius', 'humidity_percent', 'wind_speed']
        available_cols = [
            col for col in weather_cols 
            if col in laps_with_weather_df.columns and pd.notna(laps_with_weather_df[col]).any()
        ]
        
        if not available_cols:
            log.warning("No weather data available for correlation analysis.")
            return {}
        
        correlations = {}
        for col in available_cols:
            corr_value = laps_with_weather_df['lap_time_s'].corr(laps_with_weather_df[col])
            if pd.notna(corr_value):
                correlations[f"{col}_correlation"] = float(corr_value)
        
        # Generate interpretation
        interpretation = []
        significant_correlations = []
        
        for col in available_cols:
            corr_key = f"{col}_correlation"
            if corr_key in correlations:
                corr_value = correlations[corr_key]
                if abs(corr_value) > ml_config.weather_thresholds["significant_correlation"]:
                    significant_correlations.append({
                        "metric": col,
                        "correlation": corr_value,
                        "strength": "strong" if abs(corr_value) > ml_config.weather_thresholds["strong_correlation"] else "moderate"
                    })
                    
                    if col == 'track_temp_celsius':
                        if corr_value > ml_config.weather_thresholds["significant_correlation"]:
                            interpretation.append("Higher track temperatures correlate with slower lap times, likely due to tire overheating and reduced grip.")
                        elif corr_value < -ml_config.weather_thresholds["significant_correlation"]:
                            interpretation.append("Lower track temperatures correlate with slower lap times, possibly due to difficulty getting tires into optimal operating window.")
                    elif col == 'air_temp_celsius':
                        if corr_value > ml_config.weather_thresholds["significant_correlation"]:
                            interpretation.append("Higher air temperatures correlate with slower lap times, affecting engine performance and tire grip.")
                        elif corr_value < -ml_config.weather_thresholds["significant_correlation"]:
                            interpretation.append("Lower air temperatures correlate with slower lap times, affecting tire warm-up and engine efficiency.")
                    elif col == 'humidity_percent':
                        if corr_value > ml_config.weather_thresholds["significant_correlation"]:
                            interpretation.append("Higher humidity correlates with slower lap times, affecting engine power and aerodynamics.")
                    elif col == 'wind_speed':
                        if abs(corr_value) > ml_config.weather_thresholds["significant_correlation"]:
                            interpretation.append(f"Wind speed shows {'positive' if corr_value > 0 else 'negative'} correlation with lap times, affecting aerodynamics and top speed.")
        
        if not interpretation:
            interpretation.append("Weather conditions show minimal correlation with lap times in this dataset. Performance appears to be more driver/setup dependent.")
        
        return {
            "correlations": correlations,
            "significant_correlations": significant_correlations,
            "interpretation": " ".join(interpretation),
            "data_points": len(laps_with_weather_df)
        }

    def _provide_basic_weather_summary(self, weather_df: pd.DataFrame) -> Dict:
        """
        Provide basic weather summary when time-aligned analysis isn't possible.

        Args:
            weather_df: DataFrame with weather data

        Returns:
            Dictionary with basic weather summary
        """
        if weather_df.empty:
            return {"interpretation": "No weather data available."}

        summary = {
            "data_points": len(weather_df),
            "interpretation": ""
        }

        # Calculate basic weather statistics
        weather_stats = {}

        # Air temperature
        if 'air_temp_celsius' in weather_df.columns and weather_df['air_temp_celsius'].notna().any():
            temps = weather_df['air_temp_celsius'].dropna()
            weather_stats['air_temp'] = {
                'mean': float(temps.mean()),
                'min': float(temps.min()),
                'max': float(temps.max())
            }

        # Track temperature
        if 'track_temp_celsius' in weather_df.columns and weather_df['track_temp_celsius'].notna().any():
            track_temps = weather_df['track_temp_celsius'].dropna()
            weather_stats['track_temp'] = {
                'mean': float(track_temps.mean()),
                'min': float(track_temps.min()),
                'max': float(track_temps.max())
            }

        # Humidity
        if 'humidity_percent' in weather_df.columns and weather_df['humidity_percent'].notna().any():
            humidity = weather_df['humidity_percent'].dropna()
            weather_stats['humidity'] = {
                'mean': float(humidity.mean()),
                'min': float(humidity.min()),
                'max': float(humidity.max())
            }

        # Wind
        if 'wind_speed' in weather_df.columns and weather_df['wind_speed'].notna().any():
            wind = weather_df['wind_speed'].dropna()
            weather_stats['wind_speed'] = {
                'mean': float(wind.mean()),
                'max': float(wind.max())
            }

        # Rain
        if 'rain_indicator' in weather_df.columns and weather_df['rain_indicator'].notna().any():
            rain_points = (weather_df['rain_indicator'] > 0).sum()
            summary['rain_events'] = int(rain_points)

        # Generate interpretation
        interpretation_parts = []

        if 'air_temp' in weather_stats:
            temp = weather_stats['air_temp']
            interpretation_parts.append(f"Air temperature averaged {temp['mean']:.1f}°C (range: {temp['min']:.1f}-{temp['max']:.1f}°C).")

        if 'track_temp' in weather_stats:
            track_temp = weather_stats['track_temp']
            interpretation_parts.append(f"Track temperature averaged {track_temp['mean']:.1f}°C.")

        if 'humidity' in weather_stats:
            humidity = weather_stats['humidity']
            interpretation_parts.append(f"Humidity averaged {humidity['mean']:.1f}%.")

        if 'wind_speed' in weather_stats:
            wind = weather_stats['wind_speed']
            interpretation_parts.append(f"Wind speed averaged {wind['mean']:.1f} km/h (max: {wind['max']:.1f} km/h).")

        if summary.get('rain_events', 0) > 0:
            interpretation_parts.append(f"Rain was detected during {summary['rain_events']} weather readings.")
        else:
            interpretation_parts.append("No rain was detected during the race.")

        interpretation_parts.append("While detailed correlation analysis requires time-aligned lap data, these conditions provide context for race performance.")

        summary['interpretation'] = " ".join(interpretation_parts)
        summary['weather_stats'] = weather_stats

        return summary

    def _identify_best_performer(self, laps_df: pd.DataFrame) -> Optional[Dict]:
        """
        Identify best performer in these weather conditions.
        
        Args:
            laps_df: DataFrame with lap timing data
            
        Returns:
            Dictionary with best performer analysis or None
        """
        if laps_df.empty or 'vehicle_id' not in laps_df.columns or 'lap_time_s' not in laps_df.columns:
            return None
        
        # Group by vehicle and calculate statistics
        vehicle_stats = laps_df.groupby('vehicle_id')['lap_time_s'].agg([
            'mean', 'min', 'std', 'count'
        ]).reset_index()
        vehicle_stats.columns = ['vehicle_id', 'avg_lap_time', 'best_lap_time', 'std_lap_time', 'lap_count']
        
        if len(vehicle_stats) == 0:
            return None
        
        # Find best average lap time (most consistent performer)
        best_performer = vehicle_stats.loc[vehicle_stats['avg_lap_time'].idxmin()]
        best_vehicle_id = int(best_performer['vehicle_id'])
        
        # Calculate consistency (lower std = more consistent)
        consistency_score = 10.0 - min(10.0, best_performer['std_lap_time'] * 10)
        
        # Get best performer's lap data
        best_performer_laps = laps_df[laps_df['vehicle_id'] == best_vehicle_id]
        
        analysis = {
            "vehicle_id": best_vehicle_id,
            "avg_lap_time_s": float(best_performer['avg_lap_time']),
            "best_lap_time_s": float(best_performer['best_lap_time']),
            "consistency_score": float(consistency_score),
            "lap_count": int(best_performer['lap_count']),
            "std_lap_time_s": float(best_performer['std_lap_time']),
            "what_they_did_differently": (
                f"Maintained consistent pace (std: {best_performer['std_lap_time']:.3f}s) "
                f"with average lap time of {best_performer['avg_lap_time']:.3f}s. "
                f"Adapted driving style to weather conditions effectively."
            )
        }
        
        return analysis
    
    def _save_recommendations_to_firestore(self, recommendations: List[Dict]):
        """Save weather impact recommendations to Firestore ml_weather_recommendations collection."""
        if not recommendations:
            log.info("No recommendations to save.")
            return
        
        db = self._get_firestore_client()
        collection_ref = db.collection("ml_weather_recommendations")
        
        log.info(f"Saving {len(recommendations)} weather impact recommendations to Firestore...")
        
        for rec in recommendations:
            # Create document ID
            doc_id = f"race_{rec['race_id']}_weather_impact"
            
            # Prepare Firestore document
            firestore_doc = {
                "race_id": rec["race_id"],
                "vehicle_id": rec.get("vehicle_id"),
                "recommendation_type": "weather_impact",
                "analysis": rec.get("analysis", {}),
                "best_performer": rec.get("best_performer"),
                "weather_summary": rec.get("weather_summary", {}),
                "structured_data": rec,  # Full structured data
                "created_at": firestore.SERVER_TIMESTAMP,
            }
            
            collection_ref.document(doc_id).set(firestore_doc, merge=True)
            log.debug(f"Saved weather impact recommendation: {doc_id}")
        
        log.info(f"Successfully saved {len(recommendations)} weather impact recommendations to Firestore.")
    
    def run_analysis(self) -> List[Dict]:
        """
        Main analysis method.
        
        Loads data, analyzes weather impact, and saves recommendations to Firestore.
        """
        log.info("--- Starting Weather Impact Analysis ---")
        
        # Load race data
        self.race_data = self._load_race_data()
        
        if not self.race_data or not self.race_data.get('laps_data'):
            log.warning(f"No lap data found for race {self.race_id}")
            return []
        
        # Load weather data
        self.weather_data = self._load_weather_data()
        
        # Convert to DataFrames for analysis
        laps_df = pd.DataFrame(self.race_data['laps_data'])
        weather_df = pd.DataFrame(self.weather_data) if self.weather_data else pd.DataFrame()
        
        if laps_df.empty:
            log.warning("No lap data available for analysis.")
            return []
        
        # Calculate weather correlations
        correlation_analysis = self._calculate_weather_correlations(laps_df, weather_df)
        
        # Identify best performer
        best_performer = self._identify_best_performer(laps_df)
        
        # Calculate average weather conditions
        weather_summary = {}
        if not weather_df.empty:
            weather_summary = {
                "avg_air_temp_celsius": float(weather_df['air_temp_celsius'].mean()) if 'air_temp_celsius' in weather_df.columns else None,
                "avg_track_temp_celsius": float(weather_df['track_temp_celsius'].mean()) if 'track_temp_celsius' in weather_df.columns else None,
                "avg_humidity_percent": float(weather_df['humidity_percent'].mean()) if 'humidity_percent' in weather_df.columns else None,
                "avg_wind_speed": float(weather_df['wind_speed'].mean()) if 'wind_speed' in weather_df.columns else None,
                "rain_indicator": int(weather_df['rain_indicator'].max()) if 'rain_indicator' in weather_df.columns else 0,
                "data_points": len(weather_df)
            }
        
        # Get first vehicle_id for storage
        vehicle_id = int(laps_df['vehicle_id'].iloc[0]) if 'vehicle_id' in laps_df.columns and len(laps_df) > 0 else None
        
        result = {
            "type": "weather_impact",
            "race_id": self.race_id,
            "vehicle_id": vehicle_id,
            "analysis": correlation_analysis,
            "best_performer": best_performer,
            "weather_summary": weather_summary,
        }
        
        log.info("--- Weather Impact Analysis Complete ---")
        
        # Save recommendations to Firestore
        self._save_recommendations_to_firestore([result])
        
        return [result]




















