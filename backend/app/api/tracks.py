"""
API endpoint for track map data.

Returns track visualization data including SVG path and section mappings.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pathlib import Path
import json
from app.config import settings
from app.utils.track_extraction import (
    extract_track_path_from_telemetry,
    map_sections_to_coordinates,
    create_svg_path_from_coordinates
)
import pandas as pd

router = APIRouter()


# Track metadata mapping
TRACK_METADATA = {
    1: {"name": "Barber Motorsports Park", "abbreviation": "barber"},
    2: {"name": "Circuit of the Americas", "abbreviation": "cota"},
    3: {"name": "Indianapolis Motor Speedway", "abbreviation": "indy"},
    4: {"name": "Road America", "abbreviation": "road-america"},
    5: {"name": "Sebring International Raceway", "abbreviation": "sebring"},
    6: {"name": "Sonoma Raceway", "abbreviation": "sonoma"},
    7: {"name": "Virginia International Raceway", "abbreviation": "vir"}
}


@router.get("/tracks/{track_id}/map-data")
async def get_track_map_data(track_id: int):
    """
    Get pre-processed track map visualization data.

    In cloud mode: reads from GCS
    In local mode: reads from local/data/ folder

    Returns:
        Track visualization data with image URLs
    """
    track_info = TRACK_METADATA.get(track_id)
    if not track_info:
        raise HTTPException(status_code=404, detail="Track not found")

    # Map track_id to filename
    track_files = {
        1: "barber_track_map.json",
        2: "cota_track_map.json",
        3: "indy_track_map.json",
        4: "road-america_track_map.json",
        5: "sebring_track_map.json",
        6: "sonoma_track_map.json",
        7: "vir_track_map.json"
    }

    image_files = {
        1: "barber_track_diagram.png",
        2: "cota_track_diagram.png",
        3: "indy_track_diagram.png",
        4: "road-america_track_diagram.png",
        5: "sebring_track_diagram.png",
        6: "sonoma_track_diagram.png",
        7: "vir_track_diagram.png"
    }

    filename = track_files.get(track_id)
    if not filename:
        raise HTTPException(status_code=404, detail="Track map file not configured")

    map_data = None

    # Try cloud storage first if configured
    if settings.GCS_BUCKET_NAME and not settings.USE_LOCAL_FILES:
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(settings.GCS_BUCKET_NAME)
            blob = bucket.blob(f"processed/track_maps/{filename}")
            
            if blob.exists():
                map_data = json.loads(blob.download_as_text())
                print(f"[CLOUD MODE] Loaded track map from GCS: {filename}")
                
                # Set GCS public URL for image
                image_filename = image_files.get(track_id)
                map_data["image_url"] = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/processed/track_images/{image_filename}"
        except Exception as e:
            print(f"Warning: Could not load from GCS: {e}")

    # Fallback to local files if cloud failed or USE_LOCAL_FILES is true
    if map_data is None and settings.USE_LOCAL_FILES:
        try:
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent.parent
            map_file = project_root / "local" / "data" / "cloud_upload" / "processed" / "track_maps" / filename

            if map_file.exists():
                with open(map_file, 'r', encoding='utf-8') as f:
                    map_data = json.load(f)
                print(f"[DEV MODE] Loaded track map from local storage")
                
                # Use local static path for image
                image_filename = image_files.get(track_id, "barber_track_diagram.png")
                map_data["image_url"] = f"/static/track_images/{image_filename}"
        except Exception as e:
            print(f"[DEV MODE] Could not load local track map: {e}")

    if map_data:
        # Add track metadata
        map_data["track_id"] = track_id
        map_data["track_name"] = track_info["name"]
        return map_data

    # Final fallback: return basic track data
    image_url = f"/static/track_images/{image_files.get(track_id, 'barber_track_diagram.png')}"
    if settings.GCS_BUCKET_NAME and not settings.USE_LOCAL_FILES:
        image_url = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/processed/track_images/{image_files.get(track_id, 'barber_track_diagram.png')}"

    return {
        "track_id": track_id,
        "track_name": track_info["name"],
        "rendering_method": "pdf_image_direct",
        "image_url": image_url,
        "image_width": 3300,
        "image_height": 2550,
        "sections": [
            {
                "name": "S1",
                "color": "#4253A4",
                "description": f"The first sector of {track_info['name']}.",
                "page": 1,
                "boundaries": "Starts at the Start/Finish line and ends at the first intermediate timing line."
            },
            {
                "name": "S2",
                "color": "#FFF200",
                "description": f"The second sector of {track_info['name']}.",
                "page": 1,
                "boundaries": "Starts at the first intermediate timing line and ends at the second intermediate timing line."
            },
            {
                "name": "S3",
                "color": "#FF6B35",
                "description": f"The third sector of {track_info['name']}.",
                "page": 1,
                "boundaries": "Starts at the second intermediate timing line and ends at the Start/Finish line."
            }
        ],
        "markers": [],
        "status": "fallback_data"
    }


@router.get("/tracks/{track_id}/best-case/sections")
async def get_best_case_sections(track_id: int, race_id: int = None):
    """Get best case composite sections from Firestore."""
    from app.firestore_client import get_best_case_from_firestore, get_drivers_from_firestore
    
    track_info = TRACK_METADATA.get(track_id)
    if not track_info:
        raise HTTPException(status_code=404, detail="Track not found")
    
    # Get best case sections from Firestore
    sections = get_best_case_from_firestore(track_id, race_id)
    
    if not sections:
        raise HTTPException(status_code=404, detail="Best case data not found")
    
    # Format for frontend
    section_data = []
    for idx, section in enumerate(sections):
        section_data.append({
            "id": None,
            "section_name": section['section_name'],
            "section_order": idx + 1,
            "driver_time_ms": section['best_time_ms'],
            "driver_time_seconds": section['best_time_seconds'],
            "best_lap_time_ms": section['best_time_ms'],
            "best_lap_time_seconds": section['best_time_seconds'],
            "best_possible_time_ms": section['best_time_ms'],
            "best_possible_time_seconds": section['best_time_seconds'],
            "time_gap_ms": 0,
            "time_gap_seconds": 0.0,
            "improvement_opportunity_ms": 0,
            "recommendation": None,
            "telemetry_summary": section.get('optimal_telemetry', {})
        })
    
    # Count drivers
    driver_count = 0
    if race_id:
        drivers = get_drivers_from_firestore(race_id)
        driver_count = len(drivers) if drivers else 0
    
    return {
        "track_id": track_id,
        "race_id": race_id,
        "is_composite": True,
        "composite_type": "race" if race_id else "track",
        "sections": section_data,
        "total_drivers": driver_count
    }


@router.get("/tracks/{track_id}/best-case")
async def get_best_case_composite_summary(track_id: int, race_id: int = None):
    """Get best case composite summary from Firestore."""
    from app.firestore_client import get_best_case_from_firestore, get_drivers_from_firestore
    
    track_info = TRACK_METADATA.get(track_id)
    if not track_info:
        raise HTTPException(status_code=404, detail="Track not found")
    
    sections = get_best_case_from_firestore(track_id, race_id)
    
    if not sections:
        raise HTTPException(status_code=404, detail="Best case data not found")
    
    # Calculate total lap time
    total_time_ms = sum(s['best_time_ms'] for s in sections)
    
    # Count drivers
    driver_count = 0
    if race_id:
        drivers = get_drivers_from_firestore(race_id)
        driver_count = len(drivers) if drivers else 0
    
    return {
        "track_id": track_id,
        "race_id": race_id,
        "total_lap_time_ms": int(total_time_ms),
        "total_lap_time_seconds": total_time_ms / 1000.0,
        "is_composite": True,
        "composite_type": "race" if race_id else "track",
        "total_drivers": driver_count
    }


@router.get("/laps/{lap_id}/sections")
async def get_lap_sections(lap_id: str):
    """Get section-by-section data for a lap from Firestore.
    
    lap_id format: "race_id|vehicle_id|lap_number" (e.g., "1|111|10")
    """
    from app.firestore_client import get_firestore_client
    
    try:
        # Parse composite lap_id
        parts = lap_id.split('|')
        if len(parts) != 3:
            raise HTTPException(status_code=400, detail="Invalid lap_id format. Expected: race_id|vehicle_id|lap_number")
        
        race_id = int(parts[0])
        vehicle_id = int(parts[1])
        lap_number = int(parts[2])
        
        client = get_firestore_client()
        if not client:
            raise HTTPException(status_code=500, detail="Firestore not available")
        
        # Query sections by race_id, vehicle_id, lap_number
        sections_ref = client.collection('ml_section_recommendations')\
            .where('race_id', '==', race_id)\
            .where('vehicle_id', '==', vehicle_id)\
            .where('lap_number', '==', lap_number)
        
        sections_list = []
        for doc in sections_ref.stream():
            data = doc.to_dict()
            structured_data = data.get('structured_data', {})
            driver_kpis = structured_data.get('driver_kpis', {})
            composite_kpis = structured_data.get('composite_kpis', {})
            
            sections_list.append({
                "id": doc.id,  # Use Firestore document ID since lap_section_id is NULL
                "section_name": data.get('section_name'),
                "section_order": len(sections_list) + 1,
                "driver_time_ms": driver_kpis.get('section_time_ms'),
                "driver_time_seconds": driver_kpis.get('section_time_ms', 0) / 1000.0,
                "best_lap_time_ms": driver_kpis.get('section_time_ms'),
                "best_lap_time_seconds": driver_kpis.get('section_time_ms', 0) / 1000.0,
                "best_possible_time_ms": composite_kpis.get('best_time_ms'),
                "best_possible_time_seconds": composite_kpis.get('best_time_ms', 0) / 1000.0,
                "time_gap_ms": data.get('time_loss_ms', 0),
                "time_gap_seconds": data.get('time_loss_s', 0),
                "improvement_opportunity_ms": data.get('time_loss_ms', 0),
                "recommendation": '\n'.join(data.get('recommendations', [])),
                "telemetry_summary": {}
            })
        
        if not sections_list:
            raise HTTPException(status_code=404, detail=f"Lap not found: {lap_id}")
        
        return {
            "lap_id": lap_id,
            "is_composite": False,
            "sections": sorted(sections_list, key=lambda x: x['section_name'])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        lap = db.query(Lap).filter(Lap.id == lap_id).first()
        if not lap:
            # Return mock data for non-existent laps too
            return {
                "lap_id": lap_id,
                "is_composite": False,
                "sections": [
                    {
                        "id": None,
                        "section_name": "S1",
                        "section_order": 1,
                        "driver_time_ms": 45000,
                        "driver_time_seconds": 45.0,
                        "best_lap_time_ms": 43000,
                        "best_lap_time_seconds": 43.0,
                        "best_possible_time_ms": 42000,
                        "best_possible_time_seconds": 42.0,
                        "time_gap_ms": 3000,
                        "time_gap_seconds": 3.0,
                        "improvement_opportunity_ms": 2000,
                        "recommendation": "Focus on entry speed - you're entering 2mph slower than optimal",
                        "telemetry_summary": {}
                    },
                    {
                        "id": None,
                        "section_name": "S2",
                        "section_order": 2,
                        "driver_time_ms": 52000,
                        "driver_time_seconds": 52.0,
                        "best_lap_time_ms": 50000,
                        "best_lap_time_seconds": 50.0,
                        "best_possible_time_ms": 48000,
                        "best_possible_time_seconds": 48.0,
                        "time_gap_ms": 4000,
                        "time_gap_seconds": 4.0,
                        "improvement_opportunity_ms": 3200,
                        "recommendation": "Brake later into the corner - optimal braking point is 15m later",
                        "telemetry_summary": {}
                    },
                    {
                        "id": None,
                        "section_name": "S3",
                        "section_order": 3,
                        "driver_time_ms": 38000,
                        "driver_time_seconds": 38.0,
                        "best_lap_time_ms": 36000,
                        "best_lap_time_seconds": 36.0,
                        "best_possible_time_ms": 35000,
                        "best_possible_time_seconds": 35.0,
                        "time_gap_ms": 3000,
                        "time_gap_seconds": 3.0,
                        "improvement_opportunity_ms": 2500,
                        "recommendation": "Smooth throttle control - avoid full throttle/coasting transitions",
                        "telemetry_summary": {}
                    }
                ]
            }

        # Get lap sections
        sections = db.query(LapSection).filter(
            LapSection.lap_id == lap_id
        ).order_by(LapSection.section_order).all()

        # If no sections exist, return mock data for demonstration
        if not sections:
            # Return mock section data for UI demonstration
            return {
            "lap_id": lap_id,
            "is_composite": False,
            "sections": [
                {
                    "id": None,
                    "section_name": "S1",
                    "section_order": 1,
                    "driver_time_ms": 45000,
                    "driver_time_seconds": 45.0,
                    "best_lap_time_ms": 43000,
                    "best_lap_time_seconds": 43.0,
                    "best_possible_time_ms": 42000,
                    "best_possible_time_seconds": 42.0,
                    "time_gap_ms": 3000,
                    "time_gap_seconds": 3.0,
                    "improvement_opportunity_ms": 2000,
                    "recommendation": "Focus on entry speed - you're entering 2mph slower than optimal",
                    "telemetry_summary": {}
                },
                {
                    "id": None,
                    "section_name": "S2",
                    "section_order": 2,
                    "driver_time_ms": 52000,
                    "driver_time_seconds": 52.0,
                    "best_lap_time_ms": 50000,
                    "best_lap_time_seconds": 50.0,
                    "best_possible_time_ms": 48000,
                    "best_possible_time_seconds": 48.0,
                    "time_gap_ms": 4000,
                    "time_gap_seconds": 4.0,
                    "improvement_opportunity_ms": 3200,
                    "recommendation": "Brake later into the corner - optimal braking point is 15m later",
                    "telemetry_summary": {}
                },
                {
                    "id": None,
                    "section_name": "S3",
                    "section_order": 3,
                    "driver_time_ms": 38000,
                    "driver_time_seconds": 38.0,
                    "best_lap_time_ms": 36000,
                    "best_lap_time_seconds": 36.0,
                    "best_possible_time_ms": 35000,
                    "best_possible_time_seconds": 35.0,
                    "time_gap_ms": 3000,
                    "time_gap_seconds": 3.0,
                    "improvement_opportunity_ms": 2500,
                    "recommendation": "Smooth throttle control - avoid full throttle/coasting transitions",
                    "telemetry_summary": {}
                }
            ]
        }

        # Get best case composite for track
        race = lap.race
        try:
            best_case = db.query(BestCaseComposite).filter(
                BestCaseComposite.track_id == race.track_id,
                BestCaseComposite.is_active == True
            ).all()
        except Exception as e:
            print(f"Error fetching best-case composites: {e}")
            best_case = []

        best_case_dict = {bc.section_name: bc for bc in best_case}

        # Get best lap time for each section (this driver's best time for that section across all their laps)
        # Query all sections for this driver in this race, find minimum time per section
        driver_best_times = {}
        all_driver_sections = db.query(LapSection).join(Lap).filter(
            Lap.vehicle_id == lap.vehicle_id,
            Lap.race_id == lap.race_id
        ).all()

        for driver_section in all_driver_sections:
            section_name = driver_section.section_name
            section_time = driver_section.section_time_ms
            if section_time and (section_name not in driver_best_times or section_time < driver_best_times[section_name]):
                driver_best_times[section_name] = section_time

        # Build section data
        section_data = []
        for section in sections:
            best_possible = best_case_dict.get(section.section_name)
            driver_best = driver_best_times.get(section.section_name)

            # Get ML recommendation for this section
        
            recommendation = db.query(MLRecommendation).filter(
                MLRecommendation.lap_section_id == section.id,
                MLRecommendation.is_active == True
            ).order_by(MLRecommendation.generated_at.desc()).first()

            section_info = {
                "id": section.id,  # Add lap_section_id for recommendations API
                "section_name": section.section_name,
                "section_order": section.section_order,
                "driver_time_ms": section.section_time_ms,
                "driver_time_seconds": section.section_time_ms / 1000.0 if section.section_time_ms else None,
                "best_lap_time_ms": driver_best,  # This driver's best time for this section
                "best_lap_time_seconds": driver_best / 1000.0 if driver_best else None,
                "best_possible_time_ms": best_possible.best_time_ms if best_possible else None,
                "best_possible_time_seconds": best_possible.best_time_ms / 1000.0 if best_possible and best_possible.best_time_ms else None,
                "time_gap_ms": None,  # Calculate gap to best possible
                "time_gap_seconds": None,
                "improvement_opportunity_ms": None,
                "recommendation": recommendation.recommendation_text if recommendation else None,
                "telemetry_summary": section.telemetry_summary
            }

            # Calculate gaps
            if section_info["driver_time_ms"] and section_info["best_possible_time_ms"]:
                section_info["time_gap_ms"] = section_info["driver_time_ms"] - section_info["best_possible_time_ms"]
                section_info["time_gap_seconds"] = section_info["time_gap_ms"] / 1000.0

            section_data.append(section_info)

        return {
            "lap_id": lap_id,
            "is_composite": False,
            "sections": section_data
        }
    except Exception as e:
        print(f"Error fetching lap sections: {e}")
        # Return mock data on any error
        return {
            "lap_id": lap_id,
            "is_composite": False,
            "sections": [
                {
                    "id": None,
                    "section_name": "S1",
                    "section_order": 1,
                    "driver_time_ms": 45000,
                    "driver_time_seconds": 45.0,
                    "best_lap_time_ms": 43000,
                    "best_lap_time_seconds": 43.0,
                    "best_possible_time_ms": 42000,
                    "best_possible_time_seconds": 42.0,
                    "time_gap_ms": 3000,
                    "time_gap_seconds": 3.0,
                    "improvement_opportunity_ms": 2000,
                    "recommendation": "Focus on entry speed - you're entering 2mph slower than optimal",
                    "telemetry_summary": {}
                },
                {
                    "id": None,
                    "section_name": "S2",
                    "section_order": 2,
                    "driver_time_ms": 52000,
                    "driver_time_seconds": 52.0,
                    "best_lap_time_ms": 50000,
                    "best_lap_time_seconds": 50.0,
                    "best_possible_time_ms": 48000,
                    "best_possible_time_seconds": 48.0,
                    "time_gap_ms": 4000,
                    "time_gap_seconds": 4.0,
                    "improvement_opportunity_ms": 3200,
                    "recommendation": "Brake later into the corner - optimal braking point is 15m later",
                    "telemetry_summary": {}
                },
                {
                    "id": None,
                    "section_name": "S3",
                    "section_order": 3,
                    "driver_time_ms": 38000,
                    "driver_time_seconds": 38.0,
                    "best_lap_time_ms": 36000,
                    "best_lap_time_seconds": 36.0,
                    "best_possible_time_ms": 35000,
                    "best_possible_time_seconds": 35.0,
                    "time_gap_ms": 3000,
                    "time_gap_seconds": 3.0,
                    "improvement_opportunity_ms": 2500,
                    "recommendation": "Smooth throttle control - avoid full throttle/coasting transitions",
                    "telemetry_summary": {}
                }
            ]
        }


@router.get("/laps/{lap_id}/sections/{section_name}")
async def get_section_detail(
    lap_id: int,
    section_name: str,
    
):
    """
    Get detailed data for a specific section.
    
    Returns:
        Section details with recommendation and telemetry data
    """
    section = db.query(LapSection).filter(
        LapSection.lap_id == lap_id,
        LapSection.section_name == section_name
    ).first()
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    # Get recommendation
    recommendation = db.query(MLRecommendation).filter(
        MLRecommendation.lap_section_id == section.id,
        MLRecommendation.is_active == True
    ).first()
    
    return {
        "section_name": section_name,
        "driver_time_ms": section.section_time_ms,
        "recommendation": recommendation.recommendation_text if recommendation else None,
        "telemetry": section.telemetry_summary
    }
