/**
 * Track Map Component - Using PDF Image Directly
 * 
 * Displays the track diagram from PDF as-is, with interactive overlays.
 * 
 * TODO: Implement section highlighting along the actual track path.
 * 
 * See: local/TRACK-HIGHLIGHTING-IMPLEMENTATION.md for the full implementation plan.
 * This requires preprocessing track images to extract SVG paths and map section boundaries.
 * Status: Deferred - approach documented for future implementation.
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Use empty string for production (same origin), fallback to localhost for development
const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000');

function TrackMap({ trackId, currentSectionName, onSectionClick }) {
  const [trackData, setTrackData] = useState(null);
  const [imageUrl, setImageUrl] = useState('');
  const [trackSections, setTrackSections] = useState([]);
  const [hoveredSection, setHoveredSection] = useState(null);

  useEffect(() => {
    if (!trackId) return;
    
    // Load track map data
    axios.get(`${API_URL}/api/tracks/${trackId}/map-data`)
      .then(response => {
        setTrackData(response.data);
        
        // Check if using PDF image method
        if (response.data.rendering_method === 'pdf_image_direct' && response.data.image_url) {
          console.log('Using PDF image:', response.data.image_url);
          setImageUrl(`${API_URL}${response.data.image_url}`);
          setTrackSections(response.data.sections || []);
        } else {
          // Fallback to SVG method
          const path = response.data.outline_path || response.data.svg_path || '';
          setImageUrl(null);
          setTrackSections(response.data.sections || []);
        }
      })
      .catch(error => {
        console.error('Error loading track data:', error);
      });
  }, [trackId]);

  const handleSectionMouseEnter = (sectionName) => {
    setHoveredSection(sectionName);
  };

  const handleSectionMouseLeave = () => {
    setHoveredSection(null);
  };

  const handleSectionClick = (sectionName) => {
    if (onSectionClick) onSectionClick(sectionName);
  };

  // If using PDF image, render image with overlays
  if (imageUrl && trackData) {
    // VIR (track ID 7) has uneven whitespace - shift image down for better bottom clearance
    const isVIR = trackId === 7 || trackData.track_name?.toLowerCase().includes('virginia');
    const imageStyle = {
      maxWidth: '100%',
      maxHeight: '100%',
      height: 'auto',
      width: 'auto',
      display: 'block',
      objectFit: 'contain',
      objectPosition: isVIR ? 'center 60%' : 'center center', // Shift VIR down
      position: 'relative',
      zIndex: 1
    };

    return (
      <div className="track-map-container-enhanced" style={{ 
        position: 'relative', 
        width: '100%', 
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#ffffff'
      }}>
        {/* Track diagram image container */}
        <div style={{
          flex: 1,
          overflow: 'hidden', // No scrollbars
          display: 'flex',
          alignItems: isVIR ? 'flex-end' : 'center', // Align VIR to bottom
          justifyContent: 'center',
          padding: '20px',
          paddingTop: isVIR ? '10px' : '20px', // Less top padding for VIR
          paddingBottom: isVIR ? '30px' : '20px', // More bottom padding for VIR
          position: 'relative'
        }}>
          {/* Image container - clean, no filters */}
          <div style={{
            position: 'relative'
          }}>
            <img 
              src={imageUrl}
              alt={trackData.track_name || 'Track Map'}
              style={imageStyle}
            />
            
            {/* TODO: Implement section highlighting along track path
                Approach: Extract SVG path, map sections to path lengths, use stroke-dasharray */}
          </div>
        </div>
      </div>
    );
  }

  // Fallback to SVG rendering (old method)
  return (
    <div className="track-map-container-enhanced">
      <div style={{ padding: '20px', color: '#fff', textAlign: 'center' }}>
        Loading track map...
      </div>
    </div>
  );
}

export default TrackMap;









