#!/usr/bin/env python3
"""
Seeds Firestore with track and race metadata.

Why: ML jobs need track/race mappings to find correct GCS folders.
"""
import os
from google.cloud import firestore

PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('FIRESTORE_PROJECT_ID', 'your-project-id')

def seed_firestore():
    """Seed all tracks and races."""
    print("Initializing Firestore...")
    print(f"   Project: {PROJECT_ID}")
    
    db = firestore.Client(project=PROJECT_ID)
    
    # All 7 tracks
    tracks = [
        {'id': 1, 'name': 'Barber Motorsports Park', 'abbreviation': 'barber', 'folder': 'barber'},
        {'id': 2, 'name': 'Circuit of the Americas', 'abbreviation': 'cota', 'folder': 'COTA'},
        {'id': 3, 'name': 'Indianapolis Motor Speedway', 'abbreviation': 'indianapolis', 'folder': 'indianapolis'},
        {'id': 4, 'name': 'Road America', 'abbreviation': 'road-america', 'folder': 'road-america'},
        {'id': 5, 'name': 'Sebring International Raceway', 'abbreviation': 'sebring', 'folder': 'sebring'},
        {'id': 6, 'name': 'Sonoma Raceway', 'abbreviation': 'sonoma', 'folder': 'sonoma'},
        {'id': 7, 'name': 'Virginia International Raceway', 'abbreviation': 'vir', 'folder': 'virginia-international-raceway'}
    ]
    
    # All 14 races (2 per track)
    races = []
    race_id = 1
    for track in tracks:
        for race_num in [1, 2]:
            races.append({
                'id': race_id,
                'track_id': track['id'],
                'race_number': race_num,
                'track_abbreviation': track['abbreviation'],
                'track_folder': track['folder'],
                'track_name': track['name'],
                'date': f'2024-{track["id"]:02d}-{race_num:02d}'  # Placeholder
            })
            race_id += 1
    
    print(f"\nSeeding {len(tracks)} tracks...")
    for track in tracks:
        doc_ref = db.collection('tracks').document(str(track['id']))
        doc_ref.set(track)
        print(f"   Track {track['id']}: {track['name']}")
    
    print(f"\nSeeding {len(races)} races...")
    for race in races:
        doc_ref = db.collection('races').document(str(race['id']))
        doc_ref.set(race)
        print(f"   Race {race['id']}: {race['track_name']} R{race['race_number']}")
    
    print(f"\nFirestore seeded successfully!")
    print(f"   Collections: tracks, races")
    print(f"   Tracks: {len(tracks)}")
    print(f"   Races: {len(races)}")
    
    return tracks, races


if __name__ == "__main__":
    try:
        seed_firestore()
    except Exception as e:
        print(f"\nError seeding Firestore: {e}")
        print("\nMake sure:")
        print("  1. Firestore is enabled in your GCP project")
        print("  2. You're authenticated: gcloud auth application-default login")
        print(f"  3. FIRESTORE_PROJECT_ID is set: {PROJECT_ID}")
        exit(1)


