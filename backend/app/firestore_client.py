"""
Firestore client for cloud data access.

Only used when USE_LOCAL_FILES is false.
"""

try:
    from google.cloud import firestore
except ImportError:
    firestore = None

from app.config import settings
import os

_client = None


def get_firestore_client():
    """Get or create Firestore client."""
    global _client
    
    if firestore is None:
        return None
    
    # Support both PROJECT_ID setting and GOOGLE_CLOUD_PROJECT env for robustness
    project_id = getattr(settings, "PROJECT_ID", "") or os.getenv("GOOGLE_CLOUD_PROJECT", "")

    if _client is None and project_id:
        try:
            _client = firestore.Client(project=project_id)
            print(f"[CLOUD MODE] Connected to Firestore: {project_id}")
        except Exception as e:
            print(f"Warning: Could not connect to Firestore: {e}")
            _client = None
    
    return _client


def _to_int_if_numeric(value):
    """Convert a string value to int if numeric, else return original value."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def get_tracks_from_firestore():
    """Get tracks from Firestore."""
    client = get_firestore_client()
    if not client:
        return None
    
    try:
        tracks_ref = client.collection('tracks')
        tracks = []
        for doc in tracks_ref.stream():
            data = doc.to_dict()
            id_value = data.get('id')
            if id_value is None:
                id_value = _to_int_if_numeric(doc.id)
            tracks.append({
                'id': id_value,
                'name': data.get('name'),
                'abbreviation': data.get('abbreviation')
            })
        return tracks
    except Exception as e:
        print(f"Error reading tracks from Firestore: {e}")
        return None


def get_races_from_firestore(track_id: int):
    """Get races for a track from Firestore."""
    client = get_firestore_client()
    if not client:
        return None
    
    try:
        races_ref = client.collection('races').where('track_id', '==', track_id)
        races = []
        for doc in races_ref.stream():
            data = doc.to_dict()
            id_value = data.get('id')
            if id_value is None:
                id_value = _to_int_if_numeric(doc.id)
            races.append({
                'id': id_value,
                'race_number': data.get('race_number'),
                'date': data.get('date')
            })
        return races
    except Exception as e:
        print(f"Error reading races from Firestore: {e}")
        return None


def get_drivers_from_firestore(race_id: int):
    """Get drivers for a race from Firestore."""
    client = get_firestore_client()
    if not client:
        return None
    
    try:
        # Get drivers from coaching_insights collection
        insights_ref = client.collection('coaching_insights').where('race_id', '==', race_id)
        drivers = {}
        
        for doc in insights_ref.stream():
            data = doc.to_dict()
            vehicle_id = data.get('vehicle_id')
            if vehicle_id and vehicle_id not in drivers:
                drivers[vehicle_id] = {
                    'id': vehicle_id,
                    'vehicle_id': vehicle_id,
                    'car_number': data.get('car_number', str(vehicle_id))
                }
        
        return list(drivers.values())
    except Exception as e:
        print(f"Error reading drivers from Firestore: {e}")
        return None


def get_laps_from_firestore(race_id: int, vehicle_id: int):
    """Get laps for a driver in a race from Firestore."""
    client = get_firestore_client()
    if not client:
        return None
    
    try:
        # Query ml_section_recommendations for this race and vehicle
        sections_ref = client.collection('ml_section_recommendations').where('race_id', '==', race_id).where('vehicle_id', '==', vehicle_id)
        
        # Group by lap_number and calculate total lap time
        laps_dict = {}
        for doc in sections_ref.stream():
            data = doc.to_dict()
            lap_num = data.get('lap_number')
            
            if lap_num not in laps_dict:
                # Use composite key as ID: race_id|vehicle_id|lap_number
                laps_dict[lap_num] = {
                    'id': f"{race_id}|{vehicle_id}|{lap_num}",
                    'race_id': race_id,
                    'vehicle_id': vehicle_id,
                    'lap_number': lap_num,
                    'total_time_ms': 0
                }
            
            # Add section time
            structured_data = data.get('structured_data', {})
            driver_kpis = structured_data.get('driver_kpis', {})
            section_time = driver_kpis.get('section_time_ms', 0)
            laps_dict[lap_num]['total_time_ms'] += section_time
        
        # Convert to list
        laps = []
        for lap_num, lap_data in sorted(laps_dict.items()):
            laps.append({
                'id': lap_data['id'],
                'lap_number': lap_num,
                'lap_time_ms': int(lap_data['total_time_ms']),
                'is_valid': True
            })
        
        return laps
    except Exception as e:
        print(f"Error reading laps from Firestore: {e}")
        return None


def get_lap_sections_from_firestore(race_id: int, vehicle_id: int, lap_number: int):
    """Get section data for a specific lap."""
    client = get_firestore_client()
    if not client:
        return None
    
    try:
        sections_ref = client.collection('ml_section_recommendations')\
            .where('race_id', '==', race_id)\
            .where('vehicle_id', '==', vehicle_id)\
            .where('lap_number', '==', lap_number)
        
        sections = []
        for doc in sections_ref.stream():
            data = doc.to_dict()
            structured_data = data.get('structured_data', {})
            driver_kpis = structured_data.get('driver_kpis', {})
            composite_kpis = structured_data.get('composite_kpis', {})
            
            sections.append({
                'id': data.get('lap_section_id'),
                'section_name': data.get('section_name'),
                'lap_id': data.get('lap_id'),
                'lap_number': lap_number,
                'driver_time_ms': driver_kpis.get('section_time_ms'),
                'driver_time_seconds': driver_kpis.get('section_time_ms', 0) / 1000.0,
                'best_possible_time_ms': composite_kpis.get('section_time_ms'),
                'best_possible_time_seconds': composite_kpis.get('section_time_ms', 0) / 1000.0,
                'time_gap_ms': data.get('time_loss_ms', 0),
                'time_gap_seconds': data.get('time_loss_s', 0),
                'recommendations': data.get('recommendations', [])
            })
        
        return sorted(sections, key=lambda x: x['section_name'])
    except Exception as e:
        print(f"Error reading lap sections from Firestore: {e}")
        return None


def get_best_case_from_firestore(track_id: int, race_id: int = None):
    """Get best case composite sections from Firestore."""
    client = get_firestore_client()
    if not client:
        return None
    
    try:
        query = client.collection('best_case_composites').where('track_id', '==', track_id)
        
        if race_id:
            query = query.where('race_id', '==', race_id)
        
        sections = []
        for doc in query.stream():
            data = doc.to_dict()
            sections.append({
                'section_name': data.get('section_name'),
                'best_time_ms': data.get('best_time_ms'),
                'best_time_seconds': data.get('best_time_ms', 0) / 1000.0,
                'source_vehicle_id': data.get('best_vehicle_id'),
                'optimal_telemetry': data.get('optimal_telemetry_profile', {})
            })
        
        return sorted(sections, key=lambda x: x['section_name'])
    except Exception as e:
        print(f"Error reading best case from Firestore: {e}")
        return None


def get_section_recommendation_from_firestore(section_doc_id: str):
    """Get ML recommendation for a lap section using Firestore document ID."""
    client = get_firestore_client()
    if not client:
        return None
    
    try:
        # Query directly by document ID (e.g., "race_1_lap_10_vehicle_111_section_Section_1")
        doc = client.collection('ml_section_recommendations').document(section_doc_id).get()
        
        if doc.exists:
            data = doc.to_dict()
            return {
                'recommendation_type': 'section',
                'recommendation_text': '\n'.join(data.get('recommendations', [])),
                'structured_data': data.get('structured_data', {}),
                'confidence_score': 0.85,
                'model_version': 'v1.0'
            }
        
        return None
    except Exception as e:
        print(f"Error reading section recommendation from Firestore: {e}")
        return None


def get_weather_recommendation_from_firestore(race_id: int):
    """Get weather impact recommendation for a race."""
    client = get_firestore_client()
    if not client:
        return None
    
    try:
        doc = client.collection('ml_weather_recommendations').document(f'race_{race_id}_weather_impact').get()
        
        if doc.exists:
            data = doc.to_dict()
            analysis = data.get('analysis')
            
            # Extract interpretation string from analysis dict
            if analysis is None:
                analysis_text = ''
            elif isinstance(analysis, dict):
                analysis_text = analysis.get('interpretation') or analysis.get('summary') or ''
                if not analysis_text:
                    analysis_text = 'Weather analysis available. See structured data for details.'
            else:
                analysis_text = str(analysis) if analysis else ''
            
            # Ensure we always return a string
            if not isinstance(analysis_text, str):
                analysis_text = str(analysis_text) if analysis_text else ''
            
            return {
                'recommendation_type': 'weather',
                'recommendation_text': analysis_text,
                'structured_data': data.get('structured_data', {}),
                'weather_summary': data.get('weather_summary', {}),
                'best_performer': data.get('best_performer', {}),
                'confidence_score': 0.88,
                'model_version': 'v1.0'
            }
        
        return None
    except Exception as e:
        print(f"Error reading weather recommendation from Firestore: {e}")
        return None


def get_pattern_recommendation_from_firestore(race_id: int, vehicle_id: int):
    """Get pattern analysis recommendation for a driver."""
    client = get_firestore_client()
    if not client:
        return None
    
    try:
        doc = client.collection('ml_pattern_recommendations').document(f'race_{race_id}_vehicle_{vehicle_id}_pattern_analysis').get()
        
        if doc.exists:
            data = doc.to_dict()
            consistency = data.get('consistency_analysis', {}) or {}
            
            # Extract improvement_trend string from consistency_analysis dict
            if isinstance(consistency, dict):
                consistency_text = consistency.get('improvement_trend', '') or consistency.get('summary', '') or ''
                if not consistency_text and consistency:
                    consistency_text = 'Pattern analysis available. See structured data for details.'
            else:
                consistency_text = str(consistency) if consistency is not None else ''
            
            # Ensure we always return a string
            if not isinstance(consistency_text, str):
                consistency_text = str(consistency_text) if consistency_text else ''
            
            return {
                'recommendation_type': 'pattern',
                'recommendation_text': consistency_text,
                'structured_data': data.get('structured_data', {}),
                'trends': data.get('trends', {}),
                'section_patterns': data.get('section_patterns', {}),
                'confidence_score': 0.82,
                'model_version': 'v1.0'
            }
        
        return None
    except Exception as e:
        print(f"Error reading pattern recommendation from Firestore: {e}")
        return None


def get_coaching_insights_from_firestore(race_id: int, vehicle_id: int):
    """Get coaching insights (Gemma-generated analysis) for a driver."""
    client = get_firestore_client()
    if not client:
        return None
    
    try:
        doc = client.collection('coaching_insights').document(f'race_{race_id}_vehicle_{vehicle_id}').get()
        
        if doc.exists:
            data = doc.to_dict()
            gemma_analysis = data.get('gemma_analysis', {})
            
            return {
                'recommendation_type': 'coaching',
                'recommendation_text': _format_coaching_text(gemma_analysis),
                'structured_data': {
                    'data_facts': gemma_analysis.get('data_facts', {}),
                    'theories': gemma_analysis.get('theories', {}),
                    'recommendations': gemma_analysis.get('recommendations', [])
                },
                'version': data.get('version', 'v3_unbiased_lap_analysis'),
                'confidence_score': 0.90,  # Gemma analysis is high confidence
                'model_version': 'gemma-v3'
            }
        
        return None
    except Exception as e:
        print(f"Error reading coaching insights from Firestore: {e}")
        return None


def _format_coaching_text(gemma_analysis: dict) -> str:
    """Format Gemma analysis into readable text."""
    parts = []
    
    data_facts = gemma_analysis.get('data_facts', {})
    if data_facts:
        parts.append("## Key Observations")
        for key, value in data_facts.items():
            parts.append(f"{key.replace('_', ' ').title()}: {value}")
    
    theories = gemma_analysis.get('theories', {})
    if theories:
        parts.append("\n## Analysis")
        for key, value in theories.items():
            if key != 'confidence':
                parts.append(f"{value}")
    
    recommendations = gemma_analysis.get('recommendations', [])
    if recommendations:
        parts.append("\n## Recommendations")
        for rec in recommendations[:3]:  # Limit to top 3
            if isinstance(rec, dict):
                focus = rec.get('focus', '')
                action = rec.get('action', '')
                if focus and action:
                    parts.append(f"{focus}: {action}")
            else:
                parts.append(str(rec))
    
    return "\n".join(parts) if parts else "No coaching insights available."
