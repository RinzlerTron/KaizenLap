/**
 * ⚠️ PERFECT UI STATE - DO NOT MODIFY WITHOUT TESTING
 * 
 * This component is part of the tested, working UI.
 * See DOCS/UI-SPECIFICATIONS.md before making changes.
 * 
 * Critical elements:
 * - compositeType prop: 'race' or 'track' for contextual messages
 * - gap: '20px' in time-row for proper spacing
 * - Conditional text based on compositeType value
 */
import React, { useState, useEffect, useRef } from 'react';

const formatTime = (ms) => (ms / 1000).toFixed(3);

const Gap = ({ value }) => {
  if (value === null || isNaN(value)) return <span className="gap">-</span>;
  const sign = value > 0 ? '+' : '';
  const className = value > 0 ? 'gap-positive' : (value < 0 ? 'gap-negative' : '');
  return <span className={`gap ${className}`}>{sign}{formatTime(value)}</span>;
};

function SectionPanel({ section, isComposite, showBestCaseComposite, bestCaseComposite, totalDrivers = 0, compositeType = null, isDraggable = false, skipPanelStyling = false }) {
  const [position, setPosition] = useState({ x: 50, y: 50 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const panelRef = useRef(null);

  // Load saved position from localStorage
  useEffect(() => {
    if (isDraggable) {
      const saved = localStorage.getItem('sectionPanelPosition');
      if (saved) {
        try {
          const pos = JSON.parse(saved);
          setPosition(pos);
        } catch (e) {
          // Use default if parse fails
        }
      }
    }
  }, [isDraggable]);

  // Save position to localStorage
  useEffect(() => {
    if (isDraggable) {
      localStorage.setItem('sectionPanelPosition', JSON.stringify(position));
    }
  }, [position, isDraggable]);

  const handleMouseDown = (e) => {
    if (!isDraggable) return;
    // Don't drag if clicking inputs, buttons, or links
    const target = e.target;
    if (target.tagName === 'INPUT' || target.tagName === 'BUTTON' || target.tagName === 'A') return;
    // Allow dragging from anywhere on the panel
    setIsDragging(true);
    const rect = panelRef.current?.getBoundingClientRect();
    if (rect) {
      setDragStart({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
    }
    e.preventDefault();
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      if (!panelRef.current) return;
      const container = panelRef.current.parentElement;
      if (!container) return;
      
      const containerRect = container.getBoundingClientRect();
      const newX = e.clientX - containerRect.left - dragStart.x;
      const newY = e.clientY - containerRect.top - dragStart.y;
      
      // Constrain to container bounds
      const panelRect = panelRef.current.getBoundingClientRect();
      const maxX = containerRect.width - panelRect.width;
      const maxY = containerRect.height - panelRect.height;
      
      setPosition({
        x: Math.max(0, Math.min(maxX, newX)),
        y: Math.max(0, Math.min(maxY, newY))
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

  if (!section) return <SectionSkeleton />;

  const driverTime = section.driver_time_ms;
  const bestLapTime = section.best_lap_time_ms; // This driver's best time for THIS section
  const bestPossibleTime = section.best_possible_time_ms; // Best Case Composite (optimal across all drivers)

  // For composite mode, show simplified view
  if (isComposite) {
    const panelContent = (
      <div className={`section-panel ${skipPanelStyling ? '' : 'panel'}`} ref={panelRef} style={{
        ...(isDraggable ? { cursor: isDragging ? 'grabbing' : 'grab' } : {}),
        overflow: 'visible',
        maxHeight: 'none'
      }}>
        <h3 style={{ position: 'relative', paddingRight: isDraggable ? '30px' : '0', marginBottom: '20px' }}>
          Section: <span className="section-name">{section.section_name}</span>
          {isDraggable && (
            <span style={{
              position: 'absolute',
              right: '0',
              top: '50%',
              transform: 'translateY(-50%)',
              fontSize: '16px',
              opacity: 0.5,
              userSelect: 'none'
            }}>⋮⋮</span>
          )}
        </h3>
        
        {/* Best Case Composite - Simplified Display */}
        <div className="time-comparison">
          <div className="time-row" style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            padding: '12px 0',
            borderBottom: '1px solid var(--color-border)',
            marginBottom: '12px',
            gap: '20px'
          }}>
            <span className="time-label" style={{ fontWeight: 600 }}>
              {compositeType === 'race' ? 'Optimal time (this race)' : 'Optimal time across all drivers'}
            </span>
            <span className="time-value" style={{ fontSize: '1.2em', fontWeight: 600, whiteSpace: 'nowrap' }}>
              {formatTime(driverTime)}
            </span>
          </div>
          {totalDrivers > 0 && (
            <div style={{ 
              padding: '8px 0',
              fontSize: '0.9em',
              color: 'var(--color-text-secondary)',
              fontStyle: 'italic',
              marginBottom: '16px'
            }}>
              {compositeType === 'race' 
                ? `Best times from this race's ${totalDrivers} ${totalDrivers === 1 ? 'driver' : 'drivers'}`
                : `Out of ${totalDrivers} ${totalDrivers === 1 ? 'Driver' : 'Drivers'} (all races)`
              }
            </div>
          )}
        </div>

        {/* Best Case Composite Info */}
        <div className="recommendation" style={{
          marginTop: '16px',
          padding: '16px',
          backgroundColor: 'var(--color-bg-secondary)',
          borderRadius: '8px',
          border: '1px solid var(--color-border)',
          borderLeft: '4px solid var(--color-primary-blue)'
        }}>
          <h4 style={{
            margin: '0 0 8px 0',
            fontSize: '0.9em',
            fontWeight: 600,
            color: 'var(--color-primary-blue)',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            Best Case Composite
          </h4>
          <p style={{
            margin: 0,
            fontSize: '0.85em',
            lineHeight: '1.4',
            color: 'var(--color-text-primary)'
          }}>
            {section.recommendation || `This represents the optimal performance for ${section.section_name}, considering the fastest times across all drivers for this section.`}
          </p>
          <div style={{
            marginTop: '8px',
            fontSize: '0.75em',
            color: 'var(--color-text-secondary)',
            fontStyle: 'italic'
          }}>
            💡 Select "Best Case Composite" as driver to analyze optimal performance
          </div>
        </div>
      </div>
    );

    if (isDraggable) {
      return (
        <div
          style={{
            position: 'absolute',
            left: `${position.x}px`,
            top: `${position.y}px`,
            zIndex: 20,
            pointerEvents: 'auto'
          }}
          onMouseDown={handleMouseDown}
        >
          {panelContent}
        </div>
      );
    }

    return panelContent;
  }

  // Regular lap mode - show full comparison
  const panelContent = (
    <div className={`section-panel ${skipPanelStyling ? '' : 'panel'}`} ref={panelRef} style={{
      ...(isDraggable ? { cursor: isDragging ? 'grabbing' : 'grab' } : {}),
      overflow: 'visible',
      maxHeight: 'none',
      // Don't apply panel styling if skipPanelStyling is true
      ...(skipPanelStyling ? {} : {
        backgroundColor: 'var(--color-bg-panel)',
        borderRadius: '12px',
        border: '1px solid var(--color-border)',
        padding: '24px',
        boxShadow: '0 6px 20px var(--color-shadow)'
      })
    }}>
      <h3 style={{ position: 'relative', paddingRight: isDraggable ? '30px' : '0' }}>
        Section: <span className="section-name">{section.section_name}</span>
        {isDraggable && (
          <span style={{
            position: 'absolute',
            right: '0',
            top: '50%',
            transform: 'translateY(-50%)',
            fontSize: '16px',
            opacity: 0.5,
            userSelect: 'none'
          }}>⋮⋮</span>
        )}
      </h3>
      
      <div className="time-comparison">
        <div className="time-row time-label-driver">
          <span className="time-label">Current Lap:</span>
          <span className="time-value">{formatTime(driverTime)}</span>
          <Gap value={null} />
        </div>
        <div className="time-row time-label-best-lap">
          <span className="time-label">My Best ({section.section_name}):</span>
          <span className="time-value">{formatTime(bestLapTime)}</span>
          <Gap value={driverTime - bestLapTime} />
        </div>
        <div className="time-row time-label-best-possible">
          <span className="time-label">Optimal (All Drivers):</span>
          <span className="time-value">{formatTime(bestPossibleTime)}</span>
          <Gap value={driverTime - bestPossibleTime} />
        </div>
      </div>
    </div>
  );

  if (isDraggable) {
    return (
      <div
        style={{
          position: 'absolute',
          left: `${position.x}px`,
          top: `${position.y}px`,
          zIndex: 20,
          pointerEvents: 'auto'
        }}
        onMouseDown={handleMouseDown}
      >
        {panelContent}
      </div>
    );
  }

  return panelContent;
}

const SectionSkeleton = () => (
    <div className="section-panel panel" style={{
      backgroundColor: 'var(--color-bg-panel)',
      borderRadius: '12px',
      border: '1px solid var(--color-border)',
      padding: '24px',
      boxShadow: '0 6px 20px var(--color-shadow)'
    }}>
        <div className="skeleton skeleton-h3"></div>
        <div className="time-comparison">
            <div className="skeleton skeleton-row"></div>
            <div className="skeleton skeleton-row"></div>
            <div className="skeleton skeleton-row"></div>
        </div>
        <div className="skeleton skeleton-rec"></div>
    </div>
);


export default SectionPanel;