"""
SQLAlchemy models for KaizenLap database.

Defines database schema using SQLAlchemy ORM.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Track(Base):
    """Track model - represents racing tracks."""
    
    __tablename__ = "tracks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    abbreviation = Column(String(50), nullable=False, unique=True, index=True)
    map_path = Column(String(500))
    location = Column(String(255))
    country = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    races = relationship("Race", back_populates="track")


class Race(Base):
    """Race model - represents race events."""
    
    __tablename__ = "races"
    
    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False, index=True)
    race_number = Column(Integer, nullable=False)
    race_date = Column(Date)
    session_type = Column(String(50), default="race")
    data_source = Column(String(100), default="trddev", index=True)
    data_version = Column(String(50))
    weather_summary = Column(JSON)
    status = Column(String(50), default="processed", index=True)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    track = relationship("Track", back_populates="races")
    laps = relationship("Lap", back_populates="race")


class Vehicle(Base):
    """Vehicle model - represents racing vehicles (anonymized)."""
    
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(String(100), nullable=False, unique=True, index=True)
    chassis_number = Column(String(50))
    car_number = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    
    laps = relationship("Lap", back_populates="vehicle")


class Lap(Base):
    """Lap model - represents individual laps."""
    
    __tablename__ = "laps"
    
    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    lap_number = Column(Integer, nullable=False)
    lap_time_ms = Column(Integer)
    lap_start_time = Column(DateTime)
    lap_end_time = Column(DateTime)
    is_valid = Column(Boolean, default=True)
    telemetry_file_path = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())
    
    race = relationship("Race", back_populates="laps")
    vehicle = relationship("Vehicle", back_populates="laps")
    sections = relationship("LapSection", back_populates="lap")


class LapSection(Base):
    """LapSection model - represents sections within a lap."""
    
    __tablename__ = "lap_sections"
    
    id = Column(Integer, primary_key=True, index=True)
    lap_id = Column(Integer, ForeignKey("laps.id"), nullable=False, index=True)
    section_name = Column(String(50), nullable=False)
    section_time_ms = Column(Integer)
    section_order = Column(Integer)
    telemetry_summary = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    
    lap = relationship("Lap", back_populates="sections")
    recommendations = relationship("MLRecommendation", back_populates="lap_section")


class BestCaseComposite(Base):
    """BestCaseComposite model - pre-computed optimal performance.
    
    Supports both per-track (race_id=None) and per-race (race_id set) composites.
    """
    
    __tablename__ = "best_case_composites"
    
    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=True, index=True)  # None = track-level, set = race-level
    section_name = Column(String(50), nullable=False)
    best_time_ms = Column(Integer, nullable=False)
    source_lap_id = Column(Integer, ForeignKey("laps.id"))
    source_vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    optimal_telemetry_profile = Column(JSON)
    analysis_version = Column(String(50))
    data_snapshot_date = Column(Date, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MLRecommendation(Base):
    """MLRecommendation model - Gemma-generated recommendations."""
    
    __tablename__ = "ml_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    lap_section_id = Column(Integer, ForeignKey("lap_sections.id"), nullable=False, index=True)
    recommendation_type = Column(String(50), nullable=False, index=True)
    recommendation_text = Column(Text, nullable=False)
    structured_data = Column(JSON)
    model_version = Column(String(50), nullable=False)
    confidence_score = Column(Float)
    improvement_opportunity_score = Column(Float)
    generated_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True, index=True)
    
    lap_section = relationship("LapSection", back_populates="recommendations")


class WeatherData(Base):
    """WeatherData model - environmental conditions."""
    
    __tablename__ = "weather_data"
    
    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    air_temp_celsius = Column(Float)
    track_temp_celsius = Column(Float)
    humidity_percent = Column(Float)
    pressure = Column(Float)
    wind_speed = Column(Float)
    wind_direction_degrees = Column(Integer)
    rain_indicator = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class WeatherImpactAnalysis(Base):
    """WeatherImpactAnalysis model - ML-generated weather insights."""
    
    __tablename__ = "weather_impact_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False, unique=True, index=True)
    analysis_text = Column(Text, nullable=False)
    structured_insights = Column(JSON)
    model_version = Column(String(50), nullable=False)
    generated_at = Column(DateTime, server_default=func.now())


class PatternAnalysis(Base):
    """PatternAnalysis model - driver-level pattern insights."""
    
    __tablename__ = "pattern_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), index=True)
    analysis_type = Column(String(50), nullable=False, index=True)
    analysis_text = Column(Text, nullable=False)
    structured_data = Column(JSON)
    model_version = Column(String(50), nullable=False)
    data_snapshot_date = Column(Date)
    generated_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True, index=True)


class DataProcessingJob(Base):
    """DataProcessingJob model - audit trail for processing."""
    
    __tablename__ = "data_processing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(50), nullable=False, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), index=True)
    status = Column(String(50), nullable=False, index=True)
    input_data_path = Column(String(500))
    output_summary = Column(JSON)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

