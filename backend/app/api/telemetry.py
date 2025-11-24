"""
API endpoint for serving telemetry data.

Supports both cloud (GCS) and local file storage modes.
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
from app.config import settings

router = APIRouter()


@router.get("/laps/{lap_id}/telemetry")
async def get_lap_telemetry(lap_id: int):
    """
    Get processed telemetry data for a lap.
    
    In cloud mode: reads from GCS
    In local mode: reads from local/data/ folder
    
    Args:
        lap_id: Lap identifier
    
    Returns:
        Processed telemetry data (down-sampled GPS coordinates and metrics)
    """
    lap = db.query(Lap).filter(Lap.id == lap_id).first()
    if not lap:
        raise HTTPException(status_code=404, detail="Lap not found")
    
    telemetry_data = None

    # Try cloud storage first if configured
    if settings.GCS_BUCKET_NAME and not settings.USE_LOCAL_FILES:
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(settings.GCS_BUCKET_NAME)
            blob = bucket.blob(f"{settings.GCS_TELEMETRY_PREFIX}/lap_{lap_id}_telemetry.json")
            
            if blob.exists():
                telemetry_data = json.loads(blob.download_as_text())
                print(f"[CLOUD MODE] Loaded telemetry from GCS: lap_{lap_id}")
        except Exception as e:
            print(f"Warning: Could not load telemetry from GCS: {e}")

    # Fallback to local files if cloud failed or USE_LOCAL_FILES is true
    if telemetry_data is None and settings.USE_LOCAL_FILES:
        try:
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent.parent
            telemetry_file = project_root / "local" / "data" / "processed" / "telemetry" / f"lap_{lap_id}_telemetry.json"
            
            if telemetry_file.exists():
                with open(telemetry_file, 'r') as f:
                    telemetry_data = json.load(f)
                print(f"[DEV MODE] Loaded telemetry from local storage")
        except Exception as e:
            print(f"[DEV MODE] Could not load local telemetry: {e}")

    if telemetry_data:
        return telemetry_data
    
    # If not found anywhere, return empty structure
    return {
        "lap_id": lap_id,
        "status": "not_processed",
        "message": "Telemetry data not yet processed or uploaded to GCS."
    }




















