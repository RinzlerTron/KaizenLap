/**
 * Enhanced Track Map Component - Assetto Corsa style visualization.
 * 
 * Realistic track rendering with smooth curves, elevation, and racing game aesthetics.
 */
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

// Use empty string for production (same origin), fallback to localhost for development
const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000');

function TrackMap({ trackId, currentSection, sections, onSectionHover, onSectionClick }) {
  const [trackData, setTrackData] = useState(null);
  const [svgPath, setSvgPath] = useState('');
  const [trackSections, setTrackSections] = useState([]);
  const [hoveredSection, setHoveredSection] = useState(null);
  const svgRef = useRef(null);

  useEffect(() => {
    if (!trackId) return;
    
    // Load track map data - real endpoint only
    axios.get(`${API_URL}/api/tracks/${trackId}/map-data`)
      .then(response => {
        setTrackData(response.data);
        // Support both outline_path (new) and svg_path (old)
        const path = response.data.outline_path || response.data.svg_path || '';
        setSvgPath(path);
        setTrackSections(response.data.sections || []);
        console.log('Track map loaded:', {
          pathLength: path.length,
          sections: response.data.sections?.length || 0
        });
      })
      .catch(error => {
        console.error('Error loading track data:', error);
      });
  }, [trackId]);

  const handleSectionMouseEnter = (sectionName) => {
    setHoveredSection(sectionName);
    if (onSectionHover) onSectionHover(sectionName);
  };

  const handleSectionMouseLeave = () => {
    setHoveredSection(null);
  };

  const handleSectionClick = (sectionName) => {
    if (onSectionClick) onSectionClick(sectionName);
  };

  return (
    <div className="track-map-container-enhanced">
      <svg 
        ref={svgRef}
        viewBox="0 0 1000 1000" 
        className="track-map-svg-enhanced"
        style={{ width: '100%', height: 'auto' }}
      >
        {/* Background gradient - racing game style */}
        <defs>
          <linearGradient id="trackGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1a1a2e" />
            <stop offset="100%" stopColor="#16213e" />
          </linearGradient>
          
          {/* Glow effect for highlighted sections */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          
          {/* Shadow for track */}
          <filter id="trackShadow">
            <feDropShadow dx="2" dy="2" stdDeviation="3" floodColor="#000" floodOpacity="0.5"/>
          </filter>
        </defs>

        {/* Background */}
        <rect width="100%" height="100%" fill="url(#trackGradient)" />

        {/* Main track outline - ONE continuous closed loop */}
        {svgPath && (
          <>
            {/* Base shadow/outline */}
            <path
              d={svgPath}
              stroke="#000000"
              strokeWidth="14"
              fill="none"
              className="track-outline-shadow"
              opacity="0.5"
            />
            {/* Main track outline */}
            <path
              d={svgPath}
              stroke="#2a2a3e"
              strokeWidth="12"
              fill="none"
              className="track-outline-base"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </>
        )}

        {/* Colored sections - overlay colored segments on the track */}
        {trackSections && trackSections.length > 0 && trackSections.map((section, index) => {
          const isCurrent = currentSection === section.name || currentSection === section.section_name;
          const isHovered = hoveredSection === section.name || hoveredSection === section.section_name;
          const isActive = isCurrent || isHovered;
          const sectionName = section.name || section.section_name;
          const sectionPath = section.path || '';
          const sectionColor = section.color || '#555555';
          
          if (!sectionPath) return null;
          
          return (
            <g 
              key={sectionName}
              onMouseEnter={() => handleSectionMouseEnter(sectionName)}
              onMouseLeave={handleSectionMouseLeave}
              onClick={() => handleSectionClick(sectionName)}
              style={{ cursor: 'pointer' }}
            >
              {/* Colored section overlay - thicker stroke on top of base */}
              <path
                d={sectionPath}
                stroke={sectionColor}
                strokeWidth={isActive ? '13' : '11'}
                fill="none"
                className="track-section"
                opacity={isActive ? 1 : 0.9}
                filter={isActive ? 'url(#glow)' : ''}
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{
                  transition: 'all 0.3s ease',
                }}
              />
            </g>
          );
        })}

        {/* Current position indicator - racing car style */}
        {currentSection && (
          <g>
            {/* Glow circle */}
            <circle
              cx={500}
              cy={500}
              r="12"
              fill="#FF0000"
              opacity="0.3"
              className="position-glow"
            >
              <animate
                attributeName="r"
                values="12;18;12"
                dur="1s"
                repeatCount="indefinite"
              />
            </circle>
            {/* Main position dot */}
            <circle
              cx={500}
              cy={500}
              r="8"
              fill="#FF0000"
              stroke="#fff"
              strokeWidth="2"
              className="current-position-enhanced"
              filter="url(#glow)"
            />
          </g>
        )}

        {/* Racing line overlay (optional - can show optimal racing line) */}
        {svgPath && (
          <path
            d={svgPath}
            stroke="rgba(0, 255, 0, 0.3)"
            strokeWidth="2"
            strokeDasharray="5,5"
            fill="none"
            className="racing-line"
            opacity="0.5"
          />
        )}
      </svg>
    </div>
  );
}

export default TrackMap;

