"""
API routes for KaizenLap application.

Defines REST API endpoints for tracks, laps, and recommendations.
"""

from fastapi import APIRouter, HTTPException
from typing import List
from app.config import settings
from app.firestore_client import (
    get_tracks_from_firestore,
    get_races_from_firestore,
    get_drivers_from_firestore,
    get_laps_from_firestore
)

router = APIRouter()


@router.get("/tracks")
async def list_tracks():
    """
    List all available tracks.
    
    Returns:
        List of track information
    """
    # Mock tracks for fallback
    mock_tracks = [
        {"id": 1, "name": "Barber Motorsports Park", "abbreviation": "BAR"},
        {"id": 2, "name": "Circuit of the Americas", "abbreviation": "COTA"},
        {"id": 3, "name": "Indianapolis Motor Speedway", "abbreviation": "IMS"},
        {"id": 4, "name": "Road America", "abbreviation": "RA"},
        {"id": 5, "name": "Sebring International Raceway", "abbreviation": "SEB"},
        {"id": 6, "name": "Sonoma Raceway", "abbreviation": "SON"},
        {"id": 7, "name": "Virginia International Raceway", "abbreviation": "VIR"},
    ]
    
    # Try Firestore first if not in local mode
    if not settings.USE_LOCAL_FILES:
        firestore_tracks = get_tracks_from_firestore()
        if firestore_tracks:
            return firestore_tracks
    
    # Try PostgreSQL
    if db:
        try:
            tracks = db.query(Track).all()
            if tracks and len(tracks) > 0:
                return [{"id": t.id, "name": t.name, "abbreviation": t.abbreviation} for t in tracks]
        except Exception as e:
            print(f"Warning: Could not fetch tracks from database: {e}")
    
    # Fallback to mock
    return mock_tracks


@router.get("/tracks/{track_id}")
async def get_track(track_id: int):
    """
    Get track details.
    
    Args:
        track_id: Track identifier
    
    Returns:
        Track information
    """
    track_obj = db.query(Track).filter(Track.id == track_id).first()
    if not track_obj:
        raise HTTPException(status_code=404, detail="Track not found")
    return {
        "id": track_obj.id,
        "name": track_obj.name,
        "abbreviation": track_obj.abbreviation,
        "map_path": track_obj.map_path
    }


@router.get("/tracks/{track_id}/races")
async def list_races(track_id: int):
    """
    List races for a track.
    
    Args:
        track_id: Track identifier
    
    Returns:
        List of races
    """
    # Mock races for fallback
    mock_races = [
        {"id": 1, "race_number": 1, "date": "2024-01-01"},
        {"id": 2, "race_number": 2, "date": "2024-01-02"},
    ]
    
    # Try Firestore first if not in local mode
    if not settings.USE_LOCAL_FILES:
        firestore_races = get_races_from_firestore(track_id)
        if firestore_races:
            return firestore_races
    
    # Try PostgreSQL
    if db:
        try:
            races = db.query(Race).filter(Race.track_id == track_id).all()
            if races and len(races) > 0:
                return [{"id": r.id, "race_number": r.race_number, "date": str(r.race_date)} for r in races]
        except Exception as e:
            print(f"Warning: Could not fetch races from database: {e}")
    
    # Fallback to mock
    return mock_races


@router.get("/tracks/{track_id}/best-case")
async def get_best_case_composite(
    track_id: int,
    race_id: int = None,
    
):
    """
    Get best case composite for a track or specific race.

    Args:
        track_id: Track identifier
        race_id: Optional race identifier. If None, returns track-level composite (all races).
                 If set, returns race-specific composite.

    Returns:
        Best case composite data
    """
    try:
        query = db.query(BestCaseComposite).filter(
            BestCaseComposite.track_id == track_id,
            BestCaseComposite.is_active == True
        )

        if race_id is not None:
            # Per-race composite
            query = query.filter(BestCaseComposite.race_id == race_id)
        else:
            # Track-level composite (across all races)
            query = query.filter(BestCaseComposite.race_id == None)

        best_case = query.all()

        return {
            "track_id": track_id,
            "race_id": race_id,
            "composite_type": "race" if race_id else "track",
            "sections": [
                {
                    "section_name": bc.section_name,
                    "best_time_ms": bc.best_time_ms,
                    "optimal_telemetry": bc.optimal_telemetry_profile
                }
                for bc in best_case
            ]
        }
    except Exception as e:
        # Return empty data on any database error
        print(f"Error fetching best-case composite: {e}")
        return {
            "track_id": track_id,
            "race_id": race_id,
            "composite_type": "race" if race_id else "track",
            "sections": [],
            "message": "Best-case composites not available yet."
        }


@router.get("/laps/{lap_id}")
async def get_lap(lap_id: int):
    """
    Get lap details.
    
    Args:
        lap_id: Lap identifier
    
    Returns:
        Lap information
    """
    lap_obj = db.query(Lap).filter(Lap.id == lap_id).first()
    if not lap_obj:
        raise HTTPException(status_code=404, detail="Lap not found")
    return {
        "id": lap_obj.id,
        "race_id": lap_obj.race_id,
        "vehicle_id": lap_obj.vehicle_id,
        "lap_number": lap_obj.lap_number,
        "lap_time_ms": lap_obj.lap_time_ms
    }


@router.get("/laps/{lap_id}/recommendations")
async def get_lap_recommendations(lap_id: int):
    """
    Get ML-generated recommendations for a lap.
    
    Args:
        lap_id: Lap identifier
    
    Returns:
        List of recommendations per section
    """
    recommendations = db.query(MLRecommendation).join(
        LapSection
    ).filter(
        LapSection.lap_id == lap_id,
        MLRecommendation.is_active == True
    ).all()
    
    return [
        {
            "section_name": rec.lap_section.section_name,
            "recommendation_text": rec.recommendation_text,
            "improvement_opportunity_score": rec.improvement_opportunity_score,
            "recommendation_type": rec.recommendation_type
        }
        for rec in recommendations
    ]


@router.get("/tracks/{track_id}/compare")
async def compare_lap_to_best_case(
    track_id: int,
    lap_id: int,
    
):
    """
    Compare a lap to best case composite.
    
    Args:
        track_id: Track identifier
        lap_id: Lap identifier
    
    Returns:
        Comparison data with differences
    """
    # Get lap sections
    lap_sections = db.query(LapSection).filter(
        LapSection.lap_id == lap_id
    ).all()
    
    # Get best case
    best_case = db.query(BestCaseComposite).filter(
        BestCaseComposite.track_id == track_id,
        BestCaseComposite.is_active == True
    ).all()
    
    # Build comparison
    comparison = []
    for lap_sec in lap_sections:
        best_sec = next(
            (bc for bc in best_case if bc.section_name == lap_sec.section_name),
            None
        )
        if best_sec:
            comparison.append({
                "section_name": lap_sec.section_name,
                "lap_time_ms": lap_sec.section_time_ms,
                "best_time_ms": best_sec.best_time_ms,
                "time_gap_ms": lap_sec.section_time_ms - best_sec.best_time_ms if lap_sec.section_time_ms and best_sec.best_time_ms else None
            })
    
    return {"lap_id": lap_id, "comparison": comparison}


@router.get("/races/{race_id}/drivers")
async def list_drivers_for_race(race_id: int):
    """
    List all drivers (vehicles) that participated in a race.
    
    Args:
        race_id: Race identifier
    
    Returns:
        List of vehicles/drivers
    """
    # Try Firestore first if not in local mode
    if not settings.USE_LOCAL_FILES:
        firestore_drivers = get_drivers_from_firestore(race_id)
        if firestore_drivers:
            return firestore_drivers
    
    # Try PostgreSQL
    if db:
        try:
            vehicles = db.query(Vehicle).join(Lap).filter(
                Lap.race_id == race_id
            ).distinct().all()
            
            return [
                {
                    "id": v.id,
                    "vehicle_id": v.vehicle_id,
                    "car_number": v.car_number
                }
                for v in vehicles
            ]
        except Exception as e:
            print(f"Warning: Could not fetch drivers from database: {e}")
    
    # Fallback to empty list
    return []


@router.get("/drivers/{driver_id}/laps")
async def list_laps_for_driver(
    driver_id: int,
    race_id: int = None,
    
):
    """
    List laps for a driver (vehicle).
    
    Args:
        driver_id: Vehicle identifier
        race_id: Optional race filter
    
    Returns:
        List of laps
    """
    # Try Firestore first if not in local mode
    if not settings.USE_LOCAL_FILES and race_id:
        firestore_laps = get_laps_from_firestore(race_id, driver_id)
        if firestore_laps:
            return firestore_laps
    
    # Try PostgreSQL
    if db:
        try:
            query = db.query(Lap).filter(Lap.vehicle_id == driver_id)
            
            if race_id:
                query = query.filter(Lap.race_id == race_id)
            
            laps = query.order_by(Lap.lap_number).all()
            
            return [
                {
                    "id": l.id,
                    "lap_number": l.lap_number,
                    "lap_time_ms": l.lap_time_ms,
                    "race_id": l.race_id,
                    "is_valid": l.is_valid
                }
                for l in laps
            ]
        except Exception as e:
            print(f"Warning: Could not fetch laps from database: {e}")
    
    # Fallback to empty list
    return []


@router.get("/races/{race_id}/context")
async def get_race_context(race_id: int):
    """
    Get complete context for a race in one request (fixes API waterfall).
    
    Returns all data needed to populate selectors:
    - Track info
    - Race info
    - List of drivers/vehicles
    - List of laps per driver
    
    Args:
        race_id: Race identifier
    
    Returns:
        Complete race context with all related data
    """
    # Get drivers for this race
    drivers_list = get_drivers_from_firestore(race_id)
    
    if not drivers_list:
        return {
            "track": None,
            "race": {"id": race_id},
            "drivers": []
        }
    
    # Get laps for each driver
    drivers_with_laps = []
    for driver in drivers_list:
        vehicle_id = driver.get('vehicle_id') or driver.get('id')
        laps = get_laps_from_firestore(race_id, vehicle_id) or []
        
        drivers_with_laps.append({
            "id": vehicle_id,
            "vehicle_id": vehicle_id,
            "car_number": driver.get('car_number', str(vehicle_id)),
            "laps": laps
        })
    
    return {
        "track": None,  # Frontend will get this separately
        "race": {"id": race_id},
        "drivers": drivers_with_laps
    }

