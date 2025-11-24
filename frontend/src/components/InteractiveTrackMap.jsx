/**
 * Interactive Track Map Component with Zoom and Pan
 * 
 * Allows users to zoom and pan around the track map, with recommendation panels overlaid.
 */

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

// Use empty string for production (same origin), fallback to localhost for development
const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000');

function InteractiveTrackMap({ trackId, currentSectionName, onSectionClick }) {
  const [trackData, setTrackData] = useState(null);
  const [imageUrl, setImageUrl] = useState('');
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const imageRef = useRef(null);

  useEffect(() => {
    if (!trackId) return;
    
    axios.get(`${API_URL}/api/tracks/${trackId}/map-data`)
      .then(response => {
        setTrackData(response.data);
        if (response.data.rendering_method === 'pdf_image_direct' && response.data.image_url) {
          setImageUrl(`${API_URL}${response.data.image_url}`);
        }
      })
      .catch(error => {
        console.error('Error loading track data:', error);
      });
  }, [trackId]);

  // Handle mouse wheel zoom
  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.5, Math.min(3, scale * delta));
    
    // Zoom towards mouse position
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect && imageRef.current) {
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      
      const imageRect = imageRef.current.getBoundingClientRect();
      const imageX = mouseX - imageRect.left;
      const imageY = mouseY - imageRect.top;
      
      const scaleChange = newScale / scale;
      setPan({
        x: pan.x - (imageX - pan.x) * (scaleChange - 1),
        y: pan.y - (imageY - pan.y) * (scaleChange - 1)
      });
    }
    
    setScale(newScale);
  };

  // Handle mouse drag for panning
  const handleMouseDown = (e) => {
    if (e.button !== 0) return; // Only left mouse button
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragStart]);

  // Reset zoom/pan
  const handleReset = () => {
    setScale(1);
    setPan({ x: 0, y: 0 });
  };

  // VIR positioning fix
  const isVIR = trackId === 7 || trackData?.track_name?.toLowerCase().includes('virginia');

  if (!imageUrl || !trackData) {
    return (
      <div className="track-map-container-enhanced">
        <div style={{ padding: '20px', color: '#333', textAlign: 'center' }}>
          Loading track map...
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className="track-map-container-enhanced" 
      style={{ 
        position: 'relative', 
        width: '100%', 
        height: '100%',
        overflow: 'hidden',
        backgroundColor: '#ffffff',
        cursor: isDragging ? 'grabbing' : 'grab'
      }}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
    >
      {/* Zoom controls */}
      <div style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <button
          onClick={() => setScale(Math.min(3, scale * 1.2))}
          style={{
            background: 'rgba(255, 255, 255, 0.9)',
            border: '1px solid #ccc',
            color: '#333',
            padding: '8px 12px',
            borderRadius: '4px',
            cursor: 'pointer',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}
        >
          +
        </button>
        <button
          onClick={() => setScale(Math.max(0.5, scale * 0.8))}
          style={{
            background: 'rgba(255, 255, 255, 0.9)',
            border: '1px solid #ccc',
            color: '#333',
            padding: '8px 12px',
            borderRadius: '4px',
            cursor: 'pointer',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}
        >
          −
        </button>
        <button
          onClick={handleReset}
          style={{
            background: 'rgba(255, 255, 255, 0.9)',
            border: '1px solid #ccc',
            color: '#333',
            padding: '8px 12px',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}
        >
          Reset
        </button>
      </div>

      {/* Track image with transform */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: isVIR ? 'flex-end' : 'center',
        justifyContent: 'center',
        padding: '20px',
        paddingTop: isVIR ? '10px' : '20px',
        paddingBottom: isVIR ? '30px' : '20px',
        transform: `translate(${pan.x}px, ${pan.y}px)`,
        transition: isDragging ? 'none' : 'transform 0.1s ease-out'
      }}>
        <img 
          ref={imageRef}
          src={imageUrl}
          alt={trackData.track_name || 'Track Map'}
          style={{
            maxWidth: '100%',
            maxHeight: '100%',
            height: 'auto',
            width: 'auto',
            display: 'block',
            objectFit: 'contain',
            transform: `scale(${scale})`,
            transformOrigin: 'center center',
            transition: isDragging ? 'none' : 'transform 0.1s ease-out',
            objectPosition: isVIR ? 'center 60%' : 'center center',
            userSelect: 'none',
            pointerEvents: 'none'
          }}
        />
      </div>
    </div>
  );
}

export default InteractiveTrackMap;





