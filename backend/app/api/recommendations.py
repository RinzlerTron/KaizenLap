"""
API endpoints for ML-generated recommendations.

Returns AI coaching insights for drivers.
"""

from fastapi import APIRouter, HTTPException
from app.firestore_client import (
    get_section_recommendation_from_firestore,
    get_weather_recommendation_from_firestore,
    get_pattern_recommendation_from_firestore,
    get_coaching_insights_from_firestore
)

router = APIRouter()


@router.get("/sections/{lap_section_id}")
async def get_section_recommendation(lap_section_id: str):
    """Get AI recommendation for a specific lap section.
    
    lap_section_id is the Firestore document ID (e.g., "race_1_lap_10_vehicle_111_section_Section_1")
    """
    rec = get_section_recommendation_from_firestore(lap_section_id)
    
    if rec:
        return [rec]
    
    raise HTTPException(status_code=404, detail="Section recommendation not found")


@router.get("/races/{race_id}/weather-impact")
async def get_weather_impact_recommendation(race_id: int):
    """Get weather impact analysis for a race."""
    rec = get_weather_recommendation_from_firestore(race_id)
    
    if rec:
        return [rec]
    
    raise HTTPException(status_code=404, detail="Weather recommendation not found")


@router.get("/races/{race_id}/drivers/{vehicle_id}/pattern-analysis")
async def get_pattern_analysis_recommendation(race_id: int, vehicle_id: int):
    """Get pattern analysis for a specific driver in a race."""
    rec = get_pattern_recommendation_from_firestore(race_id, vehicle_id)
    
    if rec:
        return [rec]
    
    raise HTTPException(status_code=404, detail="Pattern recommendation not found")


@router.get("/races/{race_id}/drivers/{vehicle_id}/coaching-insights")
async def get_coaching_insights(race_id: int, vehicle_id: int):
    """Get coaching insights (Gemma-generated analysis) for a specific driver in a race."""
    rec = get_coaching_insights_from_firestore(race_id, vehicle_id)
    
    if rec:
        return [rec]
    
    raise HTTPException(status_code=404, detail="Coaching insights not found")
