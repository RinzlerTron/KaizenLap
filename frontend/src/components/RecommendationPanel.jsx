/**
 * Recommendation Panel Component
 * 
 * Displays ML-generated recommendations overlaid on the track map canvas.
 * Supports three types: section-level, weather impact, driver pattern.
 */

import React from 'react';
import { useApi } from '../hooks/useApi';
import Spinner from './common/Spinner';

function RecommendationPanel({ 
  recommendationType, 
  lapSectionId, 
  raceId, 
  vehicleId,
  sectionName,
  onClose 
}) {
  const endpoint = recommendationType === 'section' && lapSectionId
    ? `/api/recommendations/sections/${lapSectionId}`
    : recommendationType === 'weather' && raceId
    ? `/api/recommendations/races/${raceId}/weather-impact`
    : recommendationType === 'pattern' && raceId && vehicleId
    ? `/api/recommendations/races/${raceId}/drivers/${vehicleId}/pattern-analysis`
    : null;

  const { data: recommendations, loading, error } = useApi(endpoint);
  
  // API returns array, get first recommendation
  const recommendation = recommendations && Array.isArray(recommendations) && recommendations.length > 0
    ? recommendations[0]
    : null;

  if (!recommendationType) return null;

  const getTitle = () => {
    if (recommendationType === 'section') return `Section: ${sectionName || 'N/A'}`;
    if (recommendationType === 'weather') return 'Weather Impact Analysis';
    if (recommendationType === 'pattern') return 'Driver Pattern Analysis';
    return 'Recommendation';
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{getTitle()}</span>
        </div>
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <Spinner />
        </div>
      </div>
    );
  }

  if (error || !recommendation) {
    return (
      <div className="panel">
        <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{getTitle()}</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '20px' }}>×</button>
        </div>
        <div style={{ padding: '20px' }}>
          <p>No recommendation available yet.</p>
        </div>
      </div>
    );
  }

  const renderContent = () => {
    if (recommendationType === 'section') {
      const structured = recommendation.structured_data || {};
      return (
        <div>
          <div style={{ marginBottom: '16px' }}>
            <h3 style={{ marginBottom: '8px', fontSize: '14px', color: 'var(--color-text-secondary)' }}>What Composite Driver Did Well:</h3>
            <ul style={{ marginLeft: '20px', fontSize: '13px' }}>
              {structured.composite_kpis && typeof structured.composite_kpis === 'object' && Object.entries(structured.composite_kpis).slice(0, 3).map(([key, value]) => (
                <li key={key}>{key.replace(/_/g, ' ')}: {typeof value === 'number' ? value.toFixed(1) : String(value)}</li>
              ))}
            </ul>
          </div>
          <div style={{ marginBottom: '16px' }}>
            <h3 style={{ marginBottom: '8px', fontSize: '14px', color: 'var(--color-text-secondary)' }}>What You Did:</h3>
            <ul style={{ marginLeft: '20px', fontSize: '13px' }}>
              {structured.driver_kpis && typeof structured.driver_kpis === 'object' && Object.entries(structured.driver_kpis).slice(0, 3).map(([key, value]) => (
                <li key={key}>{key.replace(/_/g, ' ')}: {typeof value === 'number' ? value.toFixed(1) : String(value)}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3 style={{ marginBottom: '8px', fontSize: '14px', color: 'var(--color-text-primary)', fontWeight: 'bold' }}>Recommendations:</h3>
            <ul style={{ marginLeft: '20px', fontSize: '13px' }}>
              {structured.recommendations && Array.isArray(structured.recommendations) && structured.recommendations.length > 0
                ? structured.recommendations.map((rec, idx) => <li key={idx}>{String(rec)}</li>)
                : <li>{recommendation.recommendation_text || 'Review composite telemetry profile for improvement opportunities'}</li>
              }
            </ul>
          </div>
        </div>
      );
    }

    if (recommendationType === 'weather') {
      const structured = recommendation.structured_data || {};
      const bestPerformer = structured.best_performer;
      return (
        <div>
          <div style={{ marginBottom: '16px' }}>
            <h3 style={{ marginBottom: '8px', fontSize: '14px', color: 'var(--color-text-secondary)' }}>Weather Impact:</h3>
            <p style={{ fontSize: '13px' }}>{recommendation.recommendation_text || (structured.analysis && typeof structured.analysis === 'object' ? structured.analysis.interpretation : 'No analysis available')}</p>
          </div>
          {bestPerformer && typeof bestPerformer === 'object' && (
            <div>
              <h3 style={{ marginBottom: '8px', fontSize: '14px', color: 'var(--color-text-primary)', fontWeight: 'bold' }}>Best Performer in These Conditions:</h3>
              <p style={{ fontSize: '13px', marginBottom: '4px' }}>
                Vehicle {bestPerformer.vehicle_id || 'Unknown'} - 
                Avg: {typeof bestPerformer.avg_lap_time_s === 'number' ? bestPerformer.avg_lap_time_s.toFixed(3) + 's' : 'N/A'}
              </p>
              <p style={{ fontSize: '13px', fontStyle: 'italic' }}>{bestPerformer.what_they_did_differently || 'Maintained consistent performance'}</p>
            </div>
          )}
        </div>
      );
    }

    if (recommendationType === 'pattern') {
      const structured = recommendation.structured_data || {};
      return (
        <div>
          <p style={{ fontSize: '13px', marginBottom: '12px' }}>{recommendation.recommendation_text || 'No pattern analysis available'}</p>
          {structured.analysis && typeof structured.analysis === 'object' && (
            <div>
              <div style={{ marginBottom: '8px' }}>
                <strong>Strengths:</strong> {Array.isArray(structured.analysis.strengths) ? structured.analysis.strengths.join(', ') : 'None identified'}
              </div>
              <div style={{ marginBottom: '8px' }}>
                <strong>Weaknesses:</strong> {Array.isArray(structured.analysis.weaknesses) ? structured.analysis.weaknesses.join(', ') : 'None identified'}
              </div>
              <div>
                <strong>Trend:</strong> {typeof structured.analysis.trend === 'object' ? (structured.analysis.trend.interpretation || 'No trend data') : (typeof structured.analysis.trend === 'string' ? structured.analysis.trend : 'No trend data')}
              </div>
            </div>
          )}
          {structured.statistics && typeof structured.statistics === 'object' && (
            <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(0, 0, 0, 0.2)', borderRadius: '8px' }}>
              <h4 style={{ marginBottom: '8px', fontSize: '13px' }}>Statistics:</h4>
              {Object.entries(structured.statistics).map(([key, value]) => (
                <div key={key} style={{ fontSize: '12px', marginBottom: '4px' }}>
                  <strong>{key.replace(/_/g, ' ')}:</strong> {typeof value === 'number' ? value.toFixed(3) : String(value)}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    return <p>{recommendation.recommendation_text || 'No recommendation available'}</p>;
  };

  return (
    <div className="panel" style={{ minWidth: '400px', maxWidth: '600px', maxHeight: '80vh', overflowY: 'auto' }}>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{getTitle()}</span>
        <button 
          onClick={onClose} 
          style={{ 
            background: 'none', 
            border: 'none', 
            color: '#fff', 
            cursor: 'pointer', 
            fontSize: '24px',
            lineHeight: '1',
            padding: '0 8px'
          }}
        >
          ×
        </button>
      </div>
      <div style={{ padding: '16px 0' }}>
        {renderContent()}
      </div>
    </div>
  );
}

export default RecommendationPanel;





