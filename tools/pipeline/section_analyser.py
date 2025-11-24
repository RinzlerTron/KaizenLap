"""
Section Performance Analyser for KaizenLap ML Pipeline.

Purpose:
    Analyzes driver performance per track section, extracts KPIs (speed, braking, throttle),
    compares against best-case composite, and generates actionable recommendations.

Status:
    ✅ Enhanced version with GCS/Firestore integration
    Reads processed telemetry from GCS, saves recommendations to Firestore

Input:
    - Race ID (to fetch processed telemetry from GCS/Firestore)
    - Race data from Firestore/PostgreSQL
    - Best-case composite data from Firestore/PostgreSQL

Output:
    - Structured analysis with KPIs, deltas, and recommendations
    - Saved to Firestore `ml_section_recommendations` collection

Dependencies:
    - Processed telemetry from GCS (from TelemetryProcessor)
    - Best-case composite data from database/Firestore
"""

import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

# Add backend and tools/pipeline to path for imports
backend_path = Path(__file__).parent.parent.parent / "backend"
tools_pipeline_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(tools_pipeline_path))

import pandas as pd
import numpy as np
from app.config import settings
from base_analyser import BaseAnalyser
from ml_config import *
from gcs_reader import load_lap_sections_from_gcs, get_race_info_from_firestore

# Google Cloud imports
try:
    from google.cloud import storage, firestore
    from google.auth.exceptions import DefaultCredentialsError
    from google.api_core.exceptions import NotFound
except ImportError:
    storage = None
    firestore = None
    DefaultCredentialsError = Exception
    NotFound = FileNotFoundError

log = logging.getLogger(__name__)


class SectionAnalyser(BaseAnalyser):
    """
    Analyzes section performance and generates structured insights.
    
    Enhanced version that:
    - Reads processed telemetry from GCS
    - Compares driver performance to best-case composite
    - Identifies what composite driver did well
    - Generates actionable recommendations
    - Saves results to Firestore
    """
    
    def __init__(self, race_id: int, track_name: str, 
                 gcs_client: Optional[storage.Client] = None, 
                 firestore_client: Optional[firestore.Client] = None):
        """
        Initialize Section Analyser.
        
        Args:
            race_id: Race identifier
            track_name: Name of the track (e.g., "barber")
            gcs_client: Optional GCS client (will create if not provided)
            firestore_client: Optional Firestore client (will create if not provided)
        """
        super().__init__(race_id, firestore_client)
        self.track_name = track_name
        # Track maps not required - we detect sections from CSV data
        self.track = None  # Not used anymore

        self.gcs_client = gcs_client
        self.processed_telemetry_df: Optional[pd.DataFrame] = None
        self.race_data: Optional[Dict] = None
        self.best_case_data: Optional[Dict] = None
        
    def _get_gcs_client(self) -> storage.Client:
        """Initialize and return GCS client."""
        if storage is None:
            raise ImportError("google-cloud-storage is not installed.")
        
        if self.gcs_client is None:
            try:
                log.info("Initializing GCS client...")
                self.gcs_client = storage.Client(project=settings.FIRESTORE_PROJECT_ID or settings.PROJECT_ID)
            except DefaultCredentialsError as e:
                log.error(f"GCS Authentication Error: Could not find default credentials: {e}")
                raise
        return self.gcs_client
    
    def _load_processed_telemetry_from_gcs(self) -> Optional[pd.DataFrame]:
        """
        Load processed telemetry from GCS.

        Reads the GCS path from Firestore document: processed_telemetry/race_{race_id}.
        Uses gcsfs to stream data directly into pandas.
        Returns None if processed telemetry is not available.
        """
        log.info(f"Loading processed telemetry for race {self.race_id} from GCS...")

        # Get GCS path from Firestore
        db = self._get_firestore_client()
        doc_ref = db.collection("processed_telemetry").document(f"race_{self.race_id}")

        try:
            doc = doc_ref.get()
            if not doc.exists:
                log.warning(f"No processed telemetry found for race {self.race_id} in Firestore.")
                return None
        except Exception as e:
            log.warning(f"Could not access processed telemetry document for race {self.race_id}: {e}")
            return None

        doc_data = doc.to_dict()
        gcs_path = doc_data.get("gcs_path")

        if not gcs_path:
            log.warning(f"No GCS path found in processed_telemetry document for race {self.race_id}.")
            return None

        log.info(f"Found GCS path: {gcs_path}. Reading directly into pandas...")

        try:
            # Use gcsfs to read directly from GCS into pandas
            df = pd.read_csv(gcs_path)
            log.info(f"Loaded {len(df)} rows from processed telemetry via gcsfs.")
            return df
        except Exception as e:
            log.error(f"Failed to read directly from GCS with gcsfs: {e}. "
                      f"Consider installing with 'pip install gcsfs'.")
            # Fallback to downloading can be implemented here if needed, but for now we raise
            raise
    
    def _load_race_data(self) -> Dict:
        """
        Load race data (laps, sections, etc.) from GCS CSV files first, then fallback to Firestore.
        
        ⚠️ PostgreSQL is LOCAL TESTING ONLY - not used in production.
        """
        if self.race_data:
            return self.race_data
        
        # 1. Try reading lap sections CSV directly from GCS
        try:
            log.info(f"Attempting to load lap sections data from GCS for race {self.race_id}")

            # Get race info (track_name, race_number) from Firestore first
            db = self._get_firestore_client()
            race_info = get_race_info_from_firestore(self.race_id, db)

            if not race_info:
                # No fallback - Firestore is source of truth
                raise ValueError(
                    f"Race {self.race_id} not found in Firestore. "
                    f"Ensure race metadata is properly seeded in Firestore 'races' collection."
                )
            else:
                track_name = race_info.get("track_name") or self.track_name
                race_number = race_info.get("race_number", 1)

            # Read CSV from GCS
            sections_df = load_lap_sections_from_gcs(track_name, race_number)

            # Parse CSV data into expected format
            race_data = self._parse_lap_sections_csv(sections_df)

            if race_data and race_data.get('laps_data'):
                log.info(f"Loaded race data from GCS: {len(race_data.get('laps_data', []))} laps")
                self.race_data = race_data
                return race_data

        except Exception as e:
            log.warning(f"Could not load data from GCS for race {self.race_id}: {e}. Falling back to Firestore...")
        
        # 2. Fallback: Load from Firestore collections
        return self._load_race_data_from_firestore()
    
    def _parse_time_to_ms(self, time_value) -> Optional[int]:
        """
        Parse time value to milliseconds.
        
        Handles formats:
        - Numeric (seconds): 45.123 → 45123ms
        - String (MM:SS.mmm): "1:23.456" → 83456ms
        - String (HH:MM:SS.mmm): "10:23.187" → 623187ms
        
        Args:
            time_value: Time value (numeric or string)
            
        Returns:
            Time in milliseconds, or None if invalid
        """
        if pd.isna(time_value) or time_value is None:
            return None
        
        try:
            # If numeric, assume seconds
            if isinstance(time_value, (int, float)):
                return int(time_value * 1000) if time_value < 1000 else int(time_value)
            
            # If string, parse time format
            time_str = str(time_value).strip()
            
            # Handle MM:SS.mmm or HH:MM:SS.mmm format
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:
                    # MM:SS.mmm
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    total_seconds = minutes * 60 + seconds
                    return int(total_seconds * 1000)
                elif len(parts) == 3:
                    # HH:MM:SS.mmm
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = float(parts[2])
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    return int(total_seconds * 1000)
            
            # Try to parse as float (seconds)
            seconds = float(time_str)
            return int(seconds * 1000) if seconds < 1000 else int(seconds)
            
        except (ValueError, AttributeError) as e:
            log.warning(f"Could not parse time value '{time_value}': {e}")
            return None
    
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
        
        # Find lap column (columns now have leading spaces stripped)
        for col in sections_df.columns:
            col_lower = col.lower().strip()
            if col == 'LAP_NUMBER' or 'lap_number' in col_lower:
                lap_col = col
            elif col == 'LAP_TIME' or ('lap' in col_lower and 'time' in col_lower):
                lap_time_col = col
            elif col == 'NUMBER':  # Vehicle ID column
                vehicle_col = col
        
        if not lap_col:
            log.warning("Could not find lap column in CSV. Available columns: " + str(list(sections_df.columns)))
            return {"race_id": self.race_id, "laps_data": []}
        
        # Find section columns (S1, S2, S3 - now without leading spaces)
        section_cols = []
        for col in sections_df.columns:
            col_lower = col.lower()
            if col_lower.startswith('s') and len(col_lower) == 2 and col_lower[1].isdigit():
                section_cols.append(col)
            elif 'sector' in col_lower or 'section' in col_lower:
                section_cols.append(col)
        
        log.info(f"Found {len(section_cols)} section columns: {section_cols}")
        
        # Group by lap and vehicle
        laps_data = []
        grouped = sections_df.groupby([lap_col, vehicle_col] if vehicle_col else [lap_col])
        
        for group_key, group_df in grouped:
            # Extract lap_num and vehicle_id from groupby tuple
            if vehicle_col:
                lap_num, vehicle_id = group_key
                vehicle_id_value = vehicle_id
            else:
                lap_num = group_key
                vehicle_id_value = None
            
            # Get lap time
            lap_time_ms = None
            if lap_time_col and lap_time_col in group_df.columns:
                lap_time_value = group_df[lap_time_col].iloc[0]
                lap_time_ms = self._parse_time_to_ms(lap_time_value)
            
            # Extract section times
            sections_dict = {}
            for idx, section_col in enumerate(section_cols):
                section_time_value = group_df[section_col].iloc[0] if section_col in group_df.columns else None
                if pd.notna(section_time_value) and section_time_value is not None:
                    # Convert to milliseconds
                    section_time_ms = self._parse_time_to_ms(section_time_value)
                    if section_time_ms:
                        section_name = f"Section {idx + 1}"  # Match best case composite naming
                        sections_dict[section_name] = {
                            "section_id": None,  # Not available from CSV
                            "section_time_ms": section_time_ms,
                            "section_order": idx + 1,
                        }
            
            laps_data.append({
                "lap_id": None,  # Not available from CSV
                "lap_number": int(lap_num) if isinstance(lap_num, (int, float, np.integer)) and pd.notna(lap_num) else None,
                "lap_time_ms": lap_time_ms,
                "vehicle_id": vehicle_id_value,
                "sections": sections_dict,
            })
        
        return {
            "race_id": self.race_id,
            "track_id": None,  # Will be set from Firestore if needed
            "laps_data": laps_data,
        }

    def _load_best_case_composite(self, track_id: int) -> Dict:
        """
        Load best-case composite data from Firestore or PostgreSQL.
        
        Args:
            track_id: Track identifier
        """
        log.info(f"Loading best-case composite for track {track_id}...")
        
        # Try PostgreSQL first
        try:
            from app.services.ml_data_service import MLDataService
            from app.database import SessionLocal
            from sqlalchemy.exc import OperationalError

            db_session = SessionLocal()
            try:
                data_service = MLDataService(db=db_session)
                best_case = data_service.get_best_case_composite(track_id)
                if best_case:
                    log.info(f"Loaded best-case composite from PostgreSQL: {len(best_case)} sections")
                    return best_case
            finally:
                db_session.close()
        except OperationalError as e:
            log.warning(f"Could not load best-case from PostgreSQL: {e}. Trying Firestore...")
        except ImportError:
            log.warning("SQLAlchemy or MLDataService not available. Trying Firestore...")
        except Exception as e:
            log.warning(f"Could not load best-case from PostgreSQL due to unexpected error: {e}. Trying Firestore...")
        
        # Fallback: Load from Firestore
        db = self._get_firestore_client()
        composites_ref = db.collection("best_case_composites")
        composites_query = composites_ref.where("track_id", "==", track_id).where("is_active", "==", True)
        composites_docs = composites_query.stream()
        
        result = {}
        for comp_doc in composites_docs:
            comp_data = comp_doc.to_dict()
            section_name = comp_data.get("section_name")
            if section_name:
                result[section_name] = {
                    "best_time_ms": comp_data.get("best_time_ms"),
                    "optimal_telemetry_profile": comp_data.get("optimal_telemetry_profile", {})
                }
        
        log.info(f"Loaded best-case composite from Firestore: {len(result)} sections")
        return result
    
    def _extract_kpis_for_section(self, section_df: pd.DataFrame) -> Dict:
        """Extracts key performance indicators from telemetry for a single section."""
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
    
    def _calculate_deltas(self, lap_kpis: Dict, best_case_kpis: Dict) -> Dict:
        """Calculates the delta between lap KPIs and the best-case composite."""
        deltas = {}
        for key, value in lap_kpis.items():
            if key in best_case_kpis:
                deltas[f"delta_{key}"] = value - best_case_kpis[key]
        return deltas
    
    def _prioritize(self, deltas: Dict, section_time_delta_ms: float) -> Dict:
        """Prioritization based on impact score."""
        impact_score = 0
        issues = []

        # Speed delta impact
        if 'delta_apex_speed_kph' in deltas and deltas['delta_apex_speed_kph'] < ml_config.impact_scores["apex_speed_delta_kph"]:
            impact_score += ml_config.impact_scores["apex_speed_impact"]
            issues.append(f"Apex speed {abs(deltas['delta_apex_speed_kph']):.1f} kph slower.")
        
        # Braking point impact
        if 'delta_braking_point_m' in deltas:
            if deltas['delta_braking_point_m'] < ml_config.impact_scores["braking_point_early_m"]:  # Braked too early
                impact_score += ml_config.impact_scores["braking_point_early_impact"]
                issues.append(f"Braked {abs(deltas['delta_braking_point_m']):.1f}m too early.")
            elif deltas['delta_braking_point_m'] > ml_config.impact_scores["braking_point_late_m"]:  # Braked too late
                impact_score += ml_config.impact_scores["braking_point_late_impact"]
                issues.append(f"Braked {abs(deltas['delta_braking_point_m']):.1f}m too late.")
            
        # Throttle application impact
        if 'delta_throttle_on_point_m' in deltas and deltas['delta_throttle_on_point_m'] > ml_config.impact_scores["throttle_point_late_m"]:
            impact_score += ml_config.impact_scores["throttle_point_impact"]
            issues.append(f"Applied throttle {deltas['delta_throttle_on_point_m']:.1f}m later.")
            
        # Section time delta has large impact
        section_time_delta_s = section_time_delta_ms / 1000.0
        impact_score += abs(section_time_delta_s) * ml_config.impact_scores["time_delta_multiplier"]

        return {"impact_score": impact_score, "issues": issues}
    
    def _generate_recommendations(self, driver_kpis: Dict, composite_kpis: Dict, 
                                  deltas: Dict, time_delta_ms: float) -> List[str]:
        """Generate actionable recommendations based on composite driver comparison."""
        recommendations = []
        
        # Braking recommendations
        if 'delta_braking_point_m' in deltas:
            delta = deltas['delta_braking_point_m']
            if delta > ml_config.recommendation_thresholds["braking_point_late_m"]:  # Braked too late
                recommendations.append(
                    f"Brake {delta:.1f}m earlier (composite braked at "
                    f"{composite_kpis.get('braking_point_m', 'N/A')}m, "
                    f"you braked at {driver_kpis.get('braking_point_m', 'N/A')}m)"
                )
            elif delta < ml_config.recommendation_thresholds["braking_point_early_m"]:  # Braked too early
                recommendations.append(
                    f"Brake {abs(delta):.1f}m later to carry more speed "
                    f"(composite braked at {composite_kpis.get('braking_point_m', 'N/A')}m)"
                )
        
        # Speed recommendations
        if 'delta_apex_speed_kph' in deltas:
            delta = deltas['delta_apex_speed_kph']
            if delta < ml_config.recommendation_thresholds["apex_speed_slower_kph"]:  # Slower apex speed
                recommendations.append(
                    f"Increase apex speed by {abs(delta):.1f} km/h "
                    f"(composite: {composite_kpis.get('apex_speed_kph', 'N/A')} km/h, "
                    f"you: {driver_kpis.get('apex_speed_kph', 'N/A')} km/h)"
                )
        
        # Throttle recommendations
        if 'delta_throttle_on_point_m' in deltas:
            delta = deltas['delta_throttle_on_point_m']
            if delta > ml_config.recommendation_thresholds["throttle_point_late_m"]:  # Applied throttle too late
                recommendations.append(
                    f"Apply throttle {delta:.1f}m earlier "
                    f"(composite applied at {composite_kpis.get('throttle_on_point_m', 'N/A')}m)"
                )
        
        # Time on throttle percentage
        if 'delta_time_on_throttle_pct' in deltas:
            delta = deltas['delta_time_on_throttle_pct']
            if delta < ml_config.recommendation_thresholds["time_on_throttle_less_pct"]:  # Less time on throttle
                recommendations.append(
                    f"Spend more time on throttle "
                    f"(composite: {composite_kpis.get('time_on_throttle_pct', 'N/A'):.1f}%, "
                    f"you: {driver_kpis.get('time_on_throttle_pct', 'N/A'):.1f}%)"
                )
        
        # If no specific recommendations, provide general guidance
        if not recommendations and time_delta_ms > ml_config.recommendation_thresholds["min_time_delta_for_general_rec_ms"]:
            recommendations.append(
                f"Review composite telemetry profile for this section - "
                f"{time_delta_ms/1000:.3f}s improvement opportunity"
            )
        
        return recommendations
    
    def _save_recommendations_to_firestore(self, recommendations: List[Dict]):
        """Save recommendations to Firestore ml_section_recommendations collection."""
        if not recommendations:
            log.info("No recommendations to save.")
            return
        
        db = self._get_firestore_client()
        collection_ref = db.collection("ml_section_recommendations")
        
        log.info(f"Saving {len(recommendations)} recommendations to Firestore...")
        
        def convert_numpy_types(obj):
            """Convert numpy types to Python native types for Firestore."""
            if isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            elif isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return obj
        
        for rec in recommendations:
            # Create document ID from race_id, lap_number, vehicle_id, and section_name
            race_id = int(rec['race_id']) if isinstance(rec['race_id'], (np.integer, np.int64)) else rec['race_id']
            lap_num = int(rec.get('lap_number', 0)) if isinstance(rec.get('lap_number'), (np.integer, np.int64)) else rec.get('lap_number', 0)
            vehicle_id = int(rec.get('vehicle_id', 0)) if isinstance(rec.get('vehicle_id'), (np.integer, np.int64)) else rec.get('vehicle_id', 0)
            section_name = rec['section_name'].replace(' ', '_').replace('/', '_')
            
            doc_id = f"race_{race_id}_lap_{lap_num}_vehicle_{vehicle_id}_section_{section_name}"
            
            # Convert numpy types
            firestore_doc = convert_numpy_types({
                "race_id": rec["race_id"],
                "lap_id": rec.get("lap_id"),
                "lap_number": rec.get("lap_number"),
                "vehicle_id": rec.get("vehicle_id"),
                "lap_section_id": rec.get("lap_section_id"),
                "section_name": rec["section_name"],
                "recommendation_type": "section_performance",
                "time_loss_ms": rec.get("time_loss_ms"),
                "time_loss_s": rec.get("time_loss_s"),
                "priority": rec.get("priority", {}),
                "driver_kpis": rec.get("driver_kpis", {}),
                "composite_kpis": rec.get("composite_kpis", {}),
                "deltas": rec.get("deltas", {}),
                "recommendations": rec.get("recommendations", []),
                "structured_data": rec,  # Full structured data
                "created_at": firestore.SERVER_TIMESTAMP,
            })
            
            collection_ref.document(doc_id).set(firestore_doc, merge=True)
            log.debug(f"Saved recommendation: {doc_id}")
        
        log.info(f"Successfully saved {len(recommendations)} recommendations to Firestore.")
    
    def run_analysis(self) -> List[Dict]:
        """
        Main analysis method.

        Loads processed telemetry (if available) or CSV data and compares against best-case composites.
        """
        log.info("--- Starting Section Performance Analysis ---")

        # Try to load processed telemetry from GCS first
        self.processed_telemetry_df = self._load_processed_telemetry_from_gcs()

        # If processed telemetry is available, use the original analysis approach
        if self.processed_telemetry_df is not None and not self.processed_telemetry_df.empty:
            log.info("Using processed telemetry for analysis")

            # Get track_id from processed telemetry metadata
            db = self._get_firestore_client()
            doc_ref = db.collection("processed_telemetry").document(f"race_{self.race_id}")
            doc = doc_ref.get()
            track_id = doc.to_dict().get("track_id") if doc.exists else None

            if not track_id:
                raise ValueError(f"Could not determine track_id for race {self.race_id}.")

            # Load best-case composite
            self.best_case_data = self._load_best_case_composite(track_id)

            if not self.best_case_data:
                log.warning(f"No best-case composite data found for track {track_id}")
                return []

            # Analyze processed telemetry against best-case composites
            results = self._analyze_processed_telemetry()

        else:
            # Fallback: Use CSV data analysis (when processed telemetry not available)
            log.info("No processed telemetry available, using CSV data analysis")

            # Load race data from CSV
            race_data = self._load_race_data()

            if not race_data or not race_data.get('laps_data'):
                log.error(f"No CSV data available for race {self.race_id}")
                return []

            # Extract track name from race data or use provided track_name
            track_name = race_data.get('track_name') or self.track_name
            
            # If still no track name, try to get from Firestore
            if not track_name:
                db = self._get_firestore_client()
                race_info = get_race_info_from_firestore(self.race_id, db)
                if race_info:
                    track_name = race_info.get('track_name')
            
            if not track_name:
                log.error(f"Could not determine track name for race {self.race_id}. "
                         f"Ensure race metadata exists in Firestore.")
                return []

            # Load best-case composite using track name
            # Use unified track name utility for consistency
            import sys
            from pathlib import Path
            backend_path = Path(__file__).parent.parent.parent / "backend"
            sys.path.insert(0, str(backend_path))
            from app.utils.track_names import get_track_id
            
            track_id = get_track_id(track_name)

            if track_id:
                self.best_case_data = self._load_best_case_composite(track_id)
            else:
                log.warning(f"No track_id mapping found for {track_name}, skipping best-case comparison")
                self.best_case_data = None

            # Analyze CSV data
            results = self._analyze_csv_data(race_data)

        log.info(f"Generated {len(results)} section recommendations")
        return results

    def _analyze_csv_data(self, race_data: Dict) -> List[Dict]:
        """
        Analyze section performance using CSV data only (when processed telemetry is not available).

        This analyzes section timing data from CSV files against best-case composites.
        """
        results = []

        if not race_data or not race_data.get('laps_data'):
            return results

        laps_data = race_data['laps_data']
        log.info(f"Analyzing {len(laps_data)} lap records from CSV data")

        # DEBUG: Check first lap structure
        if laps_data:
            log.info(f"DEBUG: First lap keys: {laps_data[0].keys()}")
            log.info(f"DEBUG: First lap vehicle_id: {laps_data[0].get('vehicle_id')}")
            log.info(f"DEBUG: First lap sections: {laps_data[0].get('sections')}")

        # Group by vehicle to analyze consistency
        vehicle_laps = {}
        for lap in laps_data:
            vehicle_id = lap.get('vehicle_id')
            if vehicle_id:
                if vehicle_id not in vehicle_laps:
                    vehicle_laps[vehicle_id] = []
                vehicle_laps[vehicle_id].append(lap)

        log.info(f"Found {len(vehicle_laps)} vehicles in race")

        for vehicle_id, laps in vehicle_laps.items():
            log.info(f"Processing vehicle {vehicle_id} with {len(laps)} laps")

            # Analyze each lap's sections
            for lap in laps:
                lap_results = self._analyze_lap_sections_from_csv(lap, vehicle_id)
                log.info(f"DEBUG: Lap results count: {len(lap_results)}")
                results.extend(lap_results)

        log.info(f"Completed analysis of {len(results)} section performances")
        return results

    def _analyze_lap_sections_from_csv(self, lap: Dict, vehicle_id: int) -> List[Dict]:
        """
        Analyze individual lap sections from CSV data.

        Args:
            lap: Lap data from CSV
            vehicle_id: Vehicle identifier

        Returns:
            List of section analysis results
        """
        results = []
        sections = lap.get('sections', {})

        if not sections:
            return results

        # Analyze each section
        for section_name, section_data in sections.items():
            if not isinstance(section_data, dict):
                continue

            section_time_ms = section_data.get('section_time_ms') or section_data.get('time_ms')
            if section_time_ms is None or section_time_ms <= 0:
                continue

            # Compare against best-case composite if available
            improvement_delta_ms = 0
            time_delta_ms = 0
            best_time_ms = None

            if self.best_case_data and section_name in self.best_case_data:
                best_time_ms = self.best_case_data[section_name].get('best_time_ms')
                if best_time_ms:
                    time_delta_ms = section_time_ms - best_time_ms
                    # Calculate improvement potential (this is simplified)
                    improvement_delta_ms = max(0, time_delta_ms * 0.1)  # Assume 10% improvement potential

            # Create recommendation
            recommendation = self._generate_section_recommendation(
                section_name=section_name,
                time_delta_ms=time_delta_ms,
                driver_time_ms=section_time_ms,
                best_time_ms=best_time_ms or section_time_ms,
                telemetry_kpis={},  # No telemetry data available
                improvement_delta_ms=improvement_delta_ms
            )

            result = {
                "race_id": self.race_id,
                "lap_id": lap.get('lap_id'),
                "lap_number": lap.get('lap_number'),
                "vehicle_id": vehicle_id,
                "section_name": section_name,
                "recommendation_type": "section_performance",
                "time_loss_ms": time_delta_ms,
                "time_loss_s": round(time_delta_ms / 1000.0, 3) if time_delta_ms else 0,
                "priority": {"impact_score": min(abs(time_delta_ms) / 1000.0, 10.0) if time_delta_ms else 1.0},
                "driver_kpis": {
                    "section_time_ms": section_time_ms,
                    "section_time_s": round(section_time_ms / 1000.0, 3)
                },
                "composite_kpis": {
                    "best_time_ms": best_time_ms,
                    "best_time_s": round(best_time_ms / 1000.0, 3) if best_time_ms else None
                } if best_time_ms else {},
                "deltas": {
                    "time_delta_ms": time_delta_ms,
                    "time_delta_s": round(time_delta_ms / 1000.0, 3) if time_delta_ms else 0,
                    "improvement_delta_ms": improvement_delta_ms
                },
                "recommendations": [recommendation],
                "structured_data": {
                    "race_id": self.race_id,
                    "lap_number": lap.get('lap_number'),
                    "vehicle_id": vehicle_id,
                    "section_name": section_name,
                    "driver_time_ms": section_time_ms,
                    "best_time_ms": best_time_ms,
                    "time_delta_ms": time_delta_ms,
                    "recommendation_text": recommendation,
                    "priority_score": min(abs(time_delta_ms) / 1000.0, 10.0) if time_delta_ms else 1.0
                }
            }

            results.append(result)

        return results

    def _analyze_processed_telemetry(self) -> List[Dict]:
        """
        Analyze section performance using both processed telemetry and section timing data.

        This combines:
        1. Processed telemetry (distance-aligned telemetry data from telemetry processing)
        2. Section timing data (section boundaries and times from original CSV files)
        """
        results = []

        # Get the race_number from Firestore (race_id=13 might be race_number=1)
        db = self._get_firestore_client()
        race_doc = db.collection('races').document(str(self.race_id)).get()
        if not race_doc.exists:
            log.error(f"Race {self.race_id} not found in Firestore")
            return results

        race_data = race_doc.to_dict()
        race_number = race_data.get('race_number', 1)

        log.info(f"Race {self.race_id} corresponds to race number {race_number} for track {self.track_name}")

        # Load section timing data from CSV files
        try:
            from gcs_reader import load_lap_sections_from_gcs
            section_df = load_lap_sections_from_gcs(self.track_name, race_number)
        except Exception as e:
            log.error(f"Failed to load section data from GCS: {e}")
            return results

        if section_df.empty:
            log.error("No section timing data available")
            return results

        # Verify processed telemetry data is available
        if self.processed_telemetry_df is None or self.processed_telemetry_df.empty:
            log.error("No processed telemetry data available for analysis")
            return results

        log.info(f"Analyzing {len(section_df)} lap records with {len(self.processed_telemetry_df)} telemetry points")

        # Get unique vehicles/drivers in this race
        vehicles = section_df['NUMBER'].unique()
        log.info(f"Found {len(vehicles)} vehicles in race {self.race_id}")

        # Process each vehicle
        for vehicle_id in vehicles:
            vehicle_section_data = section_df[section_df['NUMBER'] == vehicle_id]
            vehicle_laps = vehicle_section_data[' LAP_NUMBER'].unique()

            log.info(f"Processing vehicle {vehicle_id} with {len(vehicle_laps)} laps")

            # Analyze each lap for this vehicle
            for lap_num in vehicle_laps:
                lap_section_data = vehicle_section_data[vehicle_section_data[' LAP_NUMBER'] == lap_num]

                if lap_section_data.empty:
                    continue

                # Filter processed telemetry for this specific lap and vehicle
                # Note: processed telemetry may not have vehicle_id, so we work with lap numbers
                lap_telemetry = self.processed_telemetry_df[
                    self.processed_telemetry_df['lap'] == lap_num
                ].copy()

                if lap_telemetry.empty:
                    log.warning(f"No processed telemetry found for lap {lap_num}")
                    continue

                # Analyze each section for this lap
                for section_name, best_case_info in self.best_case_data.items():
                    section_result = self._analyze_single_section(
                        section_name, best_case_info, lap_section_data, lap_telemetry,
                        lap_num, vehicle_id
                    )
                    if section_result:
                        results.append(section_result)

                # Also analyze any intermediate timing points (IM1, IM2, etc.)
                im_cols = [col for col in lap_section_data.columns if col.strip().startswith('IM') and col.strip().endswith('_elapsed')]
                for im_col in im_cols:
                    im_result = self._analyze_intermediate_timing(
                        im_col.strip(), lap_section_data, lap_num, vehicle_id
                    )
                    if im_result:
                        results.append(im_result)

        log.info(f"Completed analysis of {len(results)} section performances")
        return results

    def _analyze_single_section(self, section_name: str, best_case_info: Dict,
                              lap_section_data: pd.DataFrame, lap_telemetry: pd.DataFrame,
                              lap_num: int, vehicle_id: int) -> Optional[Dict]:
        """
        Analyze a single section combining timing data and telemetry KPIs.
        """
        # Map section name to CSV column (e.g., "Section 1" -> " S1")
        csv_col = f" {section_name.split()[-1]}"  # "Section 1" -> " S1"

        if csv_col not in lap_section_data.columns:
            return None

        # Get driver's section time
        driver_time_raw = lap_section_data[csv_col].iloc[0]
        if pd.isna(driver_time_raw):
            return None

        # Convert to numeric and check validity
        try:
            driver_time = float(driver_time_raw)
            if driver_time <= 0:
                return None
        except (ValueError, TypeError):
            return None

        # Convert to milliseconds (CSV is in seconds)
        driver_time_ms = driver_time * 1000

        # Get best-case time
        best_time_ms = best_case_info.get('best_time_ms', 0)
        if best_time_ms <= 0:
            return None

        # Calculate time delta
        time_delta_ms = driver_time_ms - best_time_ms
        time_delta_s = time_delta_ms / 1000.0

        # Check for improvement suggestions in the data
        improvement_col = f" {section_name.split()[-1]}_IMPROVEMENT"
        improvement_delta = 0
        if improvement_col in lap_section_data.columns:
            improvement_val = lap_section_data[improvement_col].iloc[0]
            if pd.notna(improvement_val):
                try:
                    improvement_delta = float(improvement_val) * 1000  # Convert to ms
                except (ValueError, TypeError):
                    pass

        # Extract telemetry KPIs from processed data (simplified for now)
        # In a full implementation, this would analyze speed curves, braking patterns, etc.
        telemetry_kpis = self._extract_telemetry_kpis(lap_telemetry)

        # Generate recommendation based on time difference and improvement data
        if abs(time_delta_ms) > 100:  # More than 0.1 seconds difference
            recommendation = self._generate_section_recommendation(
                section_name, time_delta_ms, driver_time_ms, best_time_ms, telemetry_kpis, improvement_delta
            )

            return {
                "type": "section_performance",
                "race_id": self.race_id,
                "lap_number": int(lap_num),
                "vehicle_id": int(vehicle_id),
                "section_name": section_name,
                "driver_time_ms": driver_time_ms,
                "best_time_ms": best_time_ms,
                "time_delta_ms": time_delta_ms,
                "time_delta_s": round(time_delta_s, 3),
                "improvement_delta_ms": improvement_delta,
                "recommendation_text": recommendation,
                "telemetry_kpis": telemetry_kpis,
                "priority_score": min(abs(time_delta_ms) / 1000.0, 10.0),  # Scale 0-10
            }

        return None

    def _analyze_intermediate_timing(self, im_col: str, lap_section_data: pd.DataFrame,
                                   lap_num: int, vehicle_id: int) -> Optional[Dict]:
        """
        Analyze intermediate timing points within sections.
        """
        if im_col not in lap_section_data.columns:
            return None

        # Get intermediate timing value
        timing_val = lap_section_data[im_col].iloc[0]
        if pd.isna(timing_val):
            return None

        try:
            timing_seconds = float(timing_val)
        except (ValueError, TypeError):
            return None

        # Convert to milliseconds
        timing_ms = timing_seconds * 1000

        # Create analysis for intermediate timing
        return {
            "type": "intermediate_timing",
            "race_id": self.race_id,
            "lap_number": int(lap_num),
            "vehicle_id": int(vehicle_id),
            "timing_point": im_col,
            "timing_ms": timing_ms,
            "timing_s": timing_seconds,
            "recommendation_text": f"Intermediate timing at {im_col}: {timing_seconds:.3f}s",
            "priority_score": 1.0,  # Low priority for intermediate timings
        }

    def _extract_telemetry_kpis(self, lap_telemetry: pd.DataFrame) -> Dict:
        """
        Extract key performance indicators from processed telemetry data.
        This is a simplified version - full implementation would analyze curves and patterns.
        """
        if lap_telemetry.empty:
            return {}

        try:
            kpis = {
                "avg_speed": float(lap_telemetry['Speed'].mean()),
                "max_speed": float(lap_telemetry['Speed'].max()),
                "avg_throttle": float(lap_telemetry['ath'].mean()) if 'ath' in lap_telemetry.columns else None,
                "braking_events": int((lap_telemetry['pbrake_f'] > 10).sum()) if 'pbrake_f' in lap_telemetry.columns else 0,
                "telemetry_points": len(lap_telemetry)
            }
            return kpis
        except Exception as e:
            log.warning(f"Failed to extract telemetry KPIs: {e}")
            return {}

    def _generate_section_recommendation(self, section_name: str, time_delta_ms: float,
                                       driver_time_ms: float, best_time_ms: float,
                                       telemetry_kpis: Dict, improvement_delta_ms: float = 0) -> str:
        """Generate detailed recommendation based on time delta, telemetry, and improvement data."""
        delta_s = time_delta_ms / 1000.0
        improvement_s = improvement_delta_ms / 1000.0

        if time_delta_ms > 0:  # Slower than best
            base_msg = f"In {section_name}, you were {abs(delta_s):.3f}s slower than the best time."

            # Add improvement suggestions if available
            if abs(improvement_delta_ms) > 50:  # More than 0.05s improvement potential
                if improvement_delta_ms > 0:
                    base_msg += f" Data suggests {abs(improvement_s):.3f}s improvement is possible."
                else:
                    base_msg += f" Data indicates {abs(improvement_s):.3f}s potential time loss."

            # Add telemetry-based insights
            if telemetry_kpis.get('braking_events', 0) > 5:
                base_msg += " Consider optimizing braking points - multiple braking events detected."
            elif telemetry_kpis.get('avg_speed', 0) < 150:  # Example threshold
                base_msg += " Focus on maintaining higher average speed through the section."

            base_msg += " Review the optimal driving line and braking zones in this section."
            return base_msg

        else:  # Faster than best (rare but possible)
            return f"In {section_name}, you were {abs(delta_s):.3f}s faster than the best time. " \
                   f"Excellent performance - maintain this level."

    def _generate_basic_recommendation(self, section_name: str, time_delta_ms: float,
                                     driver_time_ms: float, best_time_ms: float) -> str:
        """Generate basic recommendation based on time delta."""
        delta_s = time_delta_ms / 1000.0

        if time_delta_ms > 0:  # Slower than best
            return f"In {section_name}, you were {abs(delta_s):.3f}s slower than the best time. " \
                   f"Focus on optimizing your driving line and braking points in this section."
        else:  # Faster than best (unlikely but possible)
            return f"In {section_name}, you were {abs(delta_s):.3f}s faster than the best time. " \
                   f"Great performance - maintain this level."







