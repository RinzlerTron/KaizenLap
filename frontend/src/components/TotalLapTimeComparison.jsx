/**
 * ⚠️ PERFECT UI STATE - DO NOT MODIFY WITHOUT TESTING
 * 
 * This component is part of the tested, working UI.
 * See DOCS/UI-SPECIFICATIONS.md before making changes.
 * 
 * Critical elements:
 * - gap: '20px' between labels and values
 * - fontSize: '1.1em' for ALL numeric values (including gap)
 * - whiteSpace: 'nowrap' on values to prevent wrapping
 */
import React from 'react';
import Tooltip from './common/Tooltip';

const formatTime = (ms) => {
  if (!ms && ms !== 0) return '-';
  const totalSeconds = ms / 1000;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = (totalSeconds % 60).toFixed(3);
  if (minutes > 0) {
    return `${minutes}:${seconds.padStart(6, '0')}`;
  }
  return seconds;
};

const formatGap = (ms) => {
  if (ms === null || ms === undefined || isNaN(ms)) return '-';
  const sign = ms > 0 ? '+' : '';
  const className = ms > 0 ? 'gap-positive' : (ms < 0 ? 'gap-negative' : '');
  return (
    <span className={`gap ${className}`}>
      {sign}{(ms / 1000).toFixed(3)}
    </span>
  );
};

function TotalLapTimeComparison({ sections, bestCaseSections, isComposite }) {
  // Calculate driver total lap time (sum of all section times)
  const driverTotalTime = sections.reduce((sum, section) => {
    return sum + (section.driver_time_ms || 0);
  }, 0);

  // Calculate optimal/composite total lap time
  let optimalTotalTime = 0;
  
  if (isComposite) {
    // If viewing composite, use the section times directly
    optimalTotalTime = sections.reduce((sum, section) => {
      return sum + (section.driver_time_ms || 0);
    }, 0);
  } else if (bestCaseSections && bestCaseSections.length > 0) {
    // If viewing regular lap with best case data, sum best case section times
    optimalTotalTime = bestCaseSections.reduce((sum, section) => {
      return sum + (section.best_time_ms || 0);
    }, 0);
  } else {
    // Fallback: use best_possible_time_ms from sections if available
    optimalTotalTime = sections.reduce((sum, section) => {
      return sum + (section.best_possible_time_ms || 0);
    }, 0);
  }

  const timeGap = driverTotalTime - optimalTotalTime;

  // Don't show if no valid data
  if (driverTotalTime === 0 && optimalTotalTime === 0) {
    return null;
  }

  return (
    <div className="panel" style={{
      marginBottom: '16px',
      padding: '16px 20px'
    }}>
      <h3 style={{
        margin: '0 0 16px 0',
        fontSize: '1em',
        fontWeight: 600,
        color: 'var(--color-text-primary)',
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
      }}>
        Total Lap Time Comparison
      </h3>
      
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        {/* Driver Total Lap Time */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '10px 0',
          borderBottom: '1px solid var(--color-border)',
          gap: '20px'
        }}>
          <span style={{
            fontSize: '0.9em',
            color: 'var(--color-text-secondary)',
            fontWeight: 500
          }}>
            Driver Total Lap Time
          </span>
          <span style={{
            fontSize: '1.1em',
            fontWeight: 600,
            color: 'var(--color-text-primary)',
            whiteSpace: 'nowrap'
          }}>
            {formatTime(driverTotalTime)}
          </span>
        </div>

        {/* Optimal Total Lap Time */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '10px 0',
          borderBottom: '1px solid var(--color-border)',
          gap: '20px'
        }}>
          <Tooltip 
            text="The Composite represents a theoretical 'perfect lap' by combining the fastest sector times from ALL drivers on this track. It shows the ultimate potential performance across the entire field."
            position="top"
          >
            <span style={{
              fontSize: '0.9em',
              color: 'var(--color-text-secondary)',
              fontWeight: 500,
              cursor: 'help',
              borderBottom: '1px dotted var(--color-text-secondary)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              Optimal (Composite) Total Lap Time
              <span style={{ fontSize: '0.8em', opacity: 0.7 }}>ℹ️</span>
            </span>
          </Tooltip>
          <span style={{
            fontSize: '1.1em',
            fontWeight: 600,
            color: 'var(--color-text-primary)',
            whiteSpace: 'nowrap'
          }}>
            {formatTime(optimalTotalTime)}
          </span>
        </div>

        {/* Gap */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '10px 0',
          marginTop: '4px',
          gap: '20px'
        }}>
          <span style={{
            fontSize: '0.9em',
            color: 'var(--color-text-secondary)',
            fontWeight: 500
          }}>
            Gap
          </span>
          <span style={{
            fontSize: '1.1em',
            fontWeight: 600,
            whiteSpace: 'nowrap'
          }}>
            {formatGap(timeGap)}
          </span>
        </div>
      </div>
    </div>
  );
}

export default TotalLapTimeComparison;


















