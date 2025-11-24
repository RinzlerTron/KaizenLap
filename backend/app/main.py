"""
KaizenLap Backend - FastAPI Application

Main application entry point for the KaizenLap racing performance analysis platform.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from pathlib import Path
import os

from app.config import settings
from app.api import routes as routes
from app.api import tracks
from app.api import telemetry

# Try to connect to database (optional - not required for Firestore-only deployment)
try:
    from app.database import engine, Base
    Base.metadata.create_all(bind=engine)
    print("Database connection successful - full functionality available.")
except Exception as e:
    print(f"Warning: Database not available (optional). Running with Firestore only. Error: {e}")

# Initialize FastAPI application
app = FastAPI(
    title="KaizenLap API",
    description="Racing performance analysis platform with ML-powered insights",
    version="1.0.0"
)

# Initialize caching (speeds up repeated requests)
@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend(), prefix="kaizenlap-cache")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes (routes.py has built-in fallback to mock data when DB unavailable)
app.include_router(routes.router, prefix="/api", tags=["api"])
app.include_router(tracks.router, prefix="/api", tags=["tracks"])
app.include_router(telemetry.router, prefix="/api", tags=["telemetry"])

# Recommendations router - force include for development
try:
    from app.api.recommendations import router as recommendations_router
    app.include_router(recommendations_router, prefix="/api/recommendations", tags=["recommendations"])
    print("Recommendations router loaded successfully")
except Exception as e:
    print(f"Warning: Could not load recommendations router: {e}")

# Serve track images (only in development mode with local files)
if settings.USE_LOCAL_FILES:
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    track_images_dir = project_root / "local" / "data" / "cloud_upload" / "processed" / "track_images"
    if track_images_dir.exists():
        app.mount("/static/track_images", StaticFiles(directory=str(track_images_dir)), name="track_images")
        print("[DEV MODE] Serving track images from local directory")
    else:
        print("[DEV MODE] Track images directory not found - create local/data/cloud_upload/processed/track_images/")
else:
    print("[CLOUD MODE] Track images served from GCS")

# Serve static files (React build) - for bundled deployment
frontend_build_path = Path(__file__).parent.parent / "frontend" / "build"
if frontend_build_path.exists():
    # Mount static assets (JS, CSS, images, etc.)
    static_dir = frontend_build_path / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    print(f"[BUNDLED MODE] Serving React frontend from {frontend_build_path}")
    
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        """Serve React application for all non-API routes (SPA routing)."""
        # Don't intercept API routes
        if full_path.startswith("api/") or full_path == "api":
            return None
        
        # Check if requesting a specific file
        file_path = frontend_build_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        # Serve index.html for all other routes (React Router handles it)
        return FileResponse(str(frontend_build_path / "index.html"))
else:
    print("[API-ONLY MODE] No frontend build found - serving API only")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "KaizenLap API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
