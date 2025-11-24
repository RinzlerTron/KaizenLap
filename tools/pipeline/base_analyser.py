"""
Base Analyser for KaizenLap ML Pipeline.

Purpose:
    Provides a base class for ML analysis components to handle common functionality:
    - Firestore client initialization
    - Data loading from PostgreSQL with Firestore fallback

Status:
    ✅ New component to refactor duplicated code
"""

import logging
import os
from typing import Dict, List, Optional

from app.config import settings

# Google Cloud imports
try:
    from google.cloud import firestore
    from google.auth.exceptions import DefaultCredentialsError
except ImportError:
    firestore = None
    DefaultCredentialsError = Exception

log = logging.getLogger(__name__)


class BaseAnalyser:
    """Base class for ML analysis components."""
    
    def __init__(self, race_id: int, firestore_client: Optional[firestore.Client] = None):
        """
        Initialize Base Analyser.
        
        Args:
            race_id: Race identifier
            firestore_client: Optional Firestore client (will create if not provided)
        """
        self.race_id = race_id
        self.firestore_client = firestore_client

    def _get_firestore_client(self) -> firestore.Client:
        """Initialize and return Firestore client."""
        if firestore is None:
            raise ImportError("google-cloud-firestore is not installed.")
        
        if self.firestore_client is None:
            # Try environment variable first, then settings
            project_id = os.getenv("FIRESTORE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
            if not project_id:
                project_id = settings.FIRESTORE_PROJECT_ID or settings.PROJECT_ID
            
            if not project_id:
                raise ValueError("FIRESTORE_PROJECT_ID or PROJECT_ID must be set.")
            
            # Get database ID from environment or default to US database
            database_id = os.getenv("FIRESTORE_DATABASE_ID", "kaizenlap-us")
            
            try:
                log.info(f"Initializing Firestore client for project: {project_id} (database: {database_id})")
                self.firestore_client = firestore.Client(project=project_id, database=database_id)
            except DefaultCredentialsError as e:
                log.error(f"Firestore Authentication Error: {e}")
                raise
        return self.firestore_client

    def _load_race_data(self) -> Dict:
        """
        Load race data from PostgreSQL with Firestore fallback.
        """
        log.info(f"Loading race data for race {self.race_id}...")
        
        # Try PostgreSQL first
        try:
            from app.services.ml_data_service import MLDataService
            from app.database import SessionLocal
            from sqlalchemy.exc import OperationalError
            
            db_session = SessionLocal()
            try:
                data_service = MLDataService(db=db_session)
                race_data = data_service.get_race_data_for_analysis(self.race_id)
                if race_data and race_data.get('laps_data'):
                    log.info(f"Loaded race data from PostgreSQL: {len(race_data.get('laps_data', []))} laps")
                    return race_data
            finally:
                db_session.close()
        except OperationalError as e:
            log.warning(f"PostgreSQL connection failed: {e}. Trying Firestore.")
        except ImportError:
            log.warning("SQLAlchemy or MLDataService not available. Trying Firestore.")
        except Exception as e:
            log.warning(f"Could not load from PostgreSQL due to unexpected error: {e}. Trying Firestore...")

        # Fallback: Load from Firestore
        return self._load_race_data_from_firestore()

    def _load_race_data_from_firestore(self) -> Dict:
        """
        Load race data from Firestore collections.
        """
        db = self._get_firestore_client()
        
        # Get race metadata
        race_ref = db.collection("races").document(str(self.race_id))
        race_doc = race_ref.get()
        
        if not race_doc.exists:
            race_ref = db.collection("races").where("id", "==", self.race_id).limit(1)
            race_docs = list(race_ref.stream())
            if not race_docs:
                raise ValueError(f"Race {self.race_id} not found in Firestore.")
            race_data_dict = race_docs[0].to_dict()
        else:
            race_data_dict = race_doc.to_dict()
        
        track_id = race_data_dict.get("track_id")
        
        # Get laps
        laps_ref = db.collection("laps")
        laps_query = laps_ref.where("race_id", "==", self.race_id).where("is_valid", "==", True)
        laps_docs = laps_query.stream()
        
        laps_data = []
        for lap_doc in laps_docs:
            lap_data = lap_doc.to_dict()
            lap_id_value = lap_data.get("id") or lap_doc.id
            if isinstance(lap_id_value, str) and lap_id_value.isdigit():
                lap_id_value = int(lap_id_value)
            
            # Get sections for this lap
            sections_ref = db.collection("lap_sections")
            sections_query = sections_ref.where("lap_id", "==", lap_doc.id).order_by("section_order")
            sections_docs = sections_query.stream()
            
            sections_dict = {}
            for sec_doc in sections_docs:
                sec_data = sec_doc.to_dict()
                sections_dict[sec_data.get("section_name", "")] = {
                    "section_id": sec_doc.id,
                    "section_time_ms": sec_data.get("section_time_ms"),
                    "section_order": sec_data.get("section_order"),
                }

            laps_data.append({
                "lap_id": lap_id_value,
                "lap_number": lap_data.get("lap_number"),
                "lap_time_ms": lap_data.get("lap_time_ms"),
                "vehicle_id": lap_data.get("vehicle_id"),
                "sections": sections_dict,
            })
        
        log.info(f"Loaded race data from Firestore: {len(laps_data)} laps")
        
        return {
            "race_id": self.race_id,
            "track_id": track_id,
            "laps_data": laps_data,
        }
