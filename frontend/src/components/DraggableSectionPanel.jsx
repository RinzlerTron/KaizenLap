import React, { useState, useEffect, useRef } from 'react';
import SectionPanel from './SectionPanel';
import PlaybackControls from './PlaybackControls';

/**
 * Combined Section Panel with Playback Controls - Draggable and Resizable
 */
function DraggableSectionPanel({ 
  section, 
  isComposite, 
  bestCaseComposite,
  totalDrivers = 0,
  compositeType = null,
  currentSectionIndex,
  totalSections,
  onPrevious,
  onNext,
  isPlaying,
  onPlayPause
}) {
  const [position, setPosition] = useState({ x: 50, y: 50 });
  const [size, setSize] = useState({ width: 450, height: 'auto' }); // Match sidebar width
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const containerRef = useRef(null);
  const resizeHandleRef = useRef(null);

  // Load saved position and size from localStorage
  useEffect(() => {
    const savedPos = localStorage.getItem('sectionPanelPosition');
    const savedSize = localStorage.getItem('sectionPanelSize');
    
    if (savedPos) {
      try {
        const pos = JSON.parse(savedPos);
        setPosition(pos);
      } catch (e) {
        // Use default if parse fails
      }
    }
    
    if (savedSize) {
      try {
        const sz = JSON.parse(savedSize);
        setSize(sz);
      } catch (e) {
        // Use default if parse fails
      }
    }
  }, []);

  // Save position and size to localStorage
  useEffect(() => {
    localStorage.setItem('sectionPanelPosition', JSON.stringify(position));
  }, [position]);

  useEffect(() => {
    if (size.width !== 'auto' && size.height !== 'auto') {
      localStorage.setItem('sectionPanelSize', JSON.stringify(size));
    }
  }, [size]);

  const handleMouseDown = (e) => {
    // Don't drag if clicking buttons, inputs, links, or resize handle
    const target = e.target;
    const isButton = target.tagName === 'BUTTON' || target.closest('button');
    const isInput = target.tagName === 'INPUT' || target.closest('input');
    const isLink = target.tagName === 'A' || target.closest('a');
    const isResizeHandle = target === resizeHandleRef.current || resizeHandleRef.current?.contains(target);
    
    if (isResizeHandle) {
      setIsResizing(true);
      const rect = containerRef.current?.getBoundingClientRect();
      if (rect) {
        setResizeStart({
          x: e.clientX,
          y: e.clientY,
          width: rect.width,
          height: rect.height
        });
      }
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    
    if (isButton || isInput || isLink) {
      return;
    }
    
    setIsDragging(true);
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      setDragStart({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
    }
    e.preventDefault();
    e.stopPropagation();
  };

  useEffect(() => {
    if (!isDragging && !isResizing) return;

    const handleMouseMove = (e) => {
      if (isResizing && containerRef.current) {
        const deltaX = e.clientX - resizeStart.x;
        const deltaY = e.clientY - resizeStart.y;
        
        const newWidth = Math.max(350, Math.min(800, resizeStart.width + deltaX));
        const newHeight = Math.max(300, Math.min(1000, resizeStart.height + deltaY));
        
        setSize({ width: newWidth, height: newHeight });
      } else if (isDragging && containerRef.current) {
        // Use viewport coordinates for fixed positioning
        const newX = e.clientX - dragStart.x;
        const newY = e.clientY - dragStart.y;
        
        // Constrain to viewport bounds
        const containerRect = containerRef.current.getBoundingClientRect();
        const maxX = window.innerWidth - containerRect.width;
        const maxY = window.innerHeight - containerRect.height;
        
        setPosition({
          x: Math.max(0, Math.min(maxX, newX)),
          y: Math.max(0, Math.min(maxY, newY))
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, dragStart, resizeStart]);

  if (!section) return null;

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: size.width === 'auto' ? 'auto' : `${size.width}px`,
        height: size.height === 'auto' ? 'auto' : `${size.height}px`,
        zIndex: 9999,
        cursor: isDragging ? 'grabbing' : (isResizing ? 'nwse-resize' : 'grab'),
        userSelect: 'none',
        display: 'flex',
        flexDirection: 'column'
      }}
      onMouseDown={handleMouseDown}
    >
      <div style={{
        width: '100%',
        height: size.height === 'auto' ? 'auto' : '100%',
        minWidth: '350px',
        maxWidth: '450px',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'visible',
        backgroundColor: '#242830',
        borderRadius: '12px',
        border: '1px solid #3a414d',
        boxShadow: '0 6px 20px rgba(0, 0, 0, 0.5)',
        padding: '24px'
      }}>
        {/* Drag handle indicator */}
        <div style={{
          position: 'absolute',
          top: '12px',
          right: '32px',
          fontSize: '18px',
          opacity: 0.4,
          userSelect: 'none',
          pointerEvents: 'none',
          zIndex: 1
        }}>
          ⋮⋮
        </div>
        
        {/* Resize handle */}
        <div
          ref={resizeHandleRef}
          style={{
            position: 'absolute',
            bottom: 0,
            right: 0,
            width: '20px',
            height: '20px',
            cursor: 'nwse-resize',
            zIndex: 10,
            background: 'linear-gradient(to top right, transparent 0%, transparent 40%, var(--color-border) 40%, var(--color-border) 45%, transparent 45%, transparent 55%, var(--color-border) 55%, var(--color-border) 60%, transparent 60%)',
            opacity: 0.6
          }}
          onMouseDown={(e) => {
            e.stopPropagation();
            setIsResizing(true);
            const rect = containerRef.current?.getBoundingClientRect();
            if (rect) {
              setResizeStart({
                x: e.clientX,
                y: e.clientY,
                width: rect.width,
                height: rect.height
              });
            }
          }}
        />
        
        {/* Section Data */}
        <div style={{ 
          pointerEvents: isDragging || isResizing ? 'none' : 'auto',
          flex: '1 1 auto',
          overflow: 'visible'
        }}>
          <SectionPanel
            section={section}
            isComposite={isComposite}
            showBestCaseComposite={false}
            bestCaseComposite={bestCaseComposite}
            totalDrivers={totalDrivers}
            compositeType={compositeType}
            isDraggable={false}
            skipPanelStyling={true}
          />
        </div>
        
        {/* Playback Controls - integrated into same box */}
        <div style={{ 
          marginTop: '12px', 
          paddingTop: '12px', 
          borderTop: '1px solid var(--color-border)',
          pointerEvents: 'auto',
          flexShrink: 0
        }}>
          <PlaybackControls
            currentSectionIndex={currentSectionIndex}
            totalSections={totalSections}
            onPrevious={onPrevious}
            onNext={onNext}
            isPlaying={isPlaying}
            onPlayPause={onPlayPause}
          />
        </div>
      </div>
    </div>
  );
}

export default DraggableSectionPanel;
