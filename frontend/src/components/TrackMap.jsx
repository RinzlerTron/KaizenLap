import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import Spinner from './common/Spinner';
import ErrorMessage from './common/ErrorMessage';

function TrackMap({ trackId, currentSectionName, onSectionClick }) {
  const { data: trackData, loading, error } = useApi(trackId ? `/api/tracks/${trackId}/map-data` : null);
  const [hoveredSectionName, setHoveredSectionName] = useState(null);

  if (loading) {
    return (
      <div className="track-map-container-enhanced">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '16px' }}>
          <Spinner size="page" />
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '14px' }}>Loading track map...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="track-map-container-enhanced">
        <ErrorMessage message={error} />
      </div>
    );
  }

  if (!trackData) {
    return (
      <div className="track-map-container-enhanced">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '16px', padding: '40px', textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '8px' }}>📍</div>
          <h3 style={{ color: 'var(--color-text-primary)', margin: 0, fontSize: '20px', fontWeight: 600 }}>Select a Track</h3>
          <p style={{ color: 'var(--color-text-secondary)', margin: 0, fontSize: '14px' }}>Choose a track from the dropdown to view the map</p>
        </div>
      </div>
    );
  }

  // New data structure: outline_path, sections (with colors), markers
  const { outline_path, sections = [], markers = [], track_name } = trackData;
  const hasMapData = outline_path && outline_path.length > 0 && sections.length > 0;

  // If no map data, show informative message
  if (!hasMapData) {
    return (
      <div className="track-map-container-enhanced">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '16px', padding: '40px', textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '8px' }}>🗺️</div>
          <h3 style={{ color: 'var(--color-text-primary)', margin: 0, fontSize: '20px', fontWeight: 600 }}>
            {track_name || 'Track Map'}
          </h3>
          <p style={{ color: 'var(--color-text-secondary)', margin: 0, fontSize: '14px', maxWidth: '400px' }}>
            Track map visualization will appear here once the track path has been extracted from telemetry data.
            <br /><br />
            <strong>Status:</strong> Track map data not yet loaded. Run the track extraction script to generate the visualization.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="track-map-container-enhanced">
      {track_name && (
        <div style={{ position: 'absolute', top: '16px', left: '16px', zIndex: 10, padding: '8px 16px', backgroundColor: 'rgba(36, 40, 48, 0.9)', borderRadius: '6px', border: '1px solid var(--color-border)' }}>
          <h4 style={{ margin: 0, color: 'var(--color-text-primary)', fontSize: '14px', fontWeight: 600 }}>{track_name}</h4>
        </div>
      )}
      <svg viewBox="0 0 1000 1000" className="track-map-svg-enhanced">
        <defs>
          {/* Glow effect for highlighted sections */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        <g>
          {/* 1. Render the base outline track first (thick grey background) */}
          {outline_path && (
            <path 
              d={outline_path} 
              className="track-outline-base" 
              fill="none" 
              stroke="#333" 
              strokeWidth="16" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            />
          )}

          {/* 2. Render each colored section on top */}
          {sections.map(section => {
            const isCurrent = currentSectionName === section.name;
            const isHovered = hoveredSectionName === section.name;
            const isActive = isCurrent || isHovered;
            
            return (
              <path
                key={section.name}
                d={section.path}
                className={`track-section ${isCurrent ? 'current' : ''} ${isHovered ? 'hovered' : ''}`}
                stroke={section.color || '#555555'}
                strokeWidth={isActive ? "14" : "12"}
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
                onClick={() => onSectionClick(section.name)}
                onMouseEnter={() => setHoveredSectionName(section.name)}
                onMouseLeave={() => setHoveredSectionName(null)}
                style={{ 
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  filter: isActive ? 'url(#glow)' : 'none',
                  opacity: isActive ? 1 : 0.9
                }}
              />
            );
          })}

          {/* 3. Render section labels */}
          {sections.map(section => {
            const isCurrent = currentSectionName === section.name;
            // Find center point of section path (simplified - would need proper calculation)
            // For now, use a heuristic based on path length
            const pathLength = section.path ? section.path.length : 0;
            const centerX = 500; // Approximate center
            const centerY = 500;
            
            return (
              <g key={`label-${section.name}`} style={{ pointerEvents: 'none' }}>
                <rect
                  x={centerX - 20}
                  y={centerY - 12}
                  width="40"
                  height="24"
                  rx="6"
                  fill={isCurrent ? 'var(--color-primary-blue)' : 'rgba(45, 50, 59, 0.9)'}
                  stroke={section.color || '#555555'}
                  strokeWidth="1.5"
                  className="track-section-label-rect"
                />
                <text 
                  x={centerX} 
                  y={centerY + 5} 
                  className="track-section-label-text"
                  fill="#FFF"
                  fontSize="13"
                  fontWeight="700"
                >
                  {section.name}
                </text>
              </g>
            );
          })}

          {/* 4. Render markers (turns, points) */}
          {markers.map(marker => {
            const pos = marker.position || {};
            const x = pos.x || 0;
            const y = pos.y || 0;
            
            return (
              <g 
                key={marker.label} 
                transform={`translate(${x}, ${y})`}
                style={{ pointerEvents: 'none' }}
              >
                <circle 
                  r="15" 
                  fill="rgba(36, 40, 48, 0.9)" 
                  stroke="#FFF" 
                  strokeWidth="1.5"
                />
                <text
                  x="0"
                  y="5"
                  textAnchor="middle"
                  fill="#FFF"
                  fontSize="12"
                  fontWeight="bold"
                >
                  {marker.label}
                </text>
              </g>
            );
          })}

          {/* 5. Current position indicator */}
          {currentSectionName && (
            (() => {
              const currentSection = sections.find(s => s.name === currentSectionName);
              if (!currentSection) return null;
              
              // Simplified position - would need proper calculation from section path
              return (
                <g>
                  <circle
                    cx={500}
                    cy={500}
                    r="10"
                    fill="#FF0000"
                    stroke="#FFF"
                    strokeWidth="2"
                    className="current-position-marker"
                    filter="url(#glow)"
                  />
                </g>
              );
            })()
          )}
        </g>
      </svg>
    </div>
  );
}

export default TrackMap;
