import React, { useState, useRef, useEffect } from 'react';
import {
  Paper, Box, Typography, IconButton,
  Chip, Divider, Button, Tooltip as MuiTooltip
} from '@mui/material';
import {
  Close, DragIndicator, Psychology, Cloud, TrendingUp, School, InfoOutlined
} from '@mui/icons-material';
import { useApi } from '../hooks/useApi';

/**
 * Draggable Recommendation Panel - Shows AI-generated insights
 */
const DraggableRecommendationPanel = ({
  recommendationType,
  lapSectionId,
  raceId,
  vehicleId,
  sectionName,
  onClose
}) => {
  const [position, setPosition] = useState({ x: window.innerWidth - 450, y: 100 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const panelRef = useRef(null);

  // API endpoint based on recommendation type
  const endpoint = recommendationType === 'section' && lapSectionId
    ? `/api/recommendations/sections/${lapSectionId}`
    : recommendationType === 'weather' && raceId
    ? `/api/recommendations/races/${raceId}/weather-impact`
    : recommendationType === 'pattern' && raceId && vehicleId
    ? `/api/recommendations/races/${raceId}/drivers/${vehicleId}/pattern-analysis`
    : recommendationType === 'coaching' && raceId && vehicleId
    ? `/api/recommendations/races/${raceId}/drivers/${vehicleId}/coaching-insights`
    : null;

  const { data: recommendations, loading, error } = useApi(endpoint);

  // Safety check: ensure recommendations is valid
  useEffect(() => {
    if (error) {
      console.error('Recommendation API error:', error);
    }
    if (recommendations && !Array.isArray(recommendations)) {
      console.warn('Recommendations is not an array:', recommendations);
    }
  }, [recommendations, error]);

  // Get recommendation data (API returns array)
  const recommendation = recommendations && Array.isArray(recommendations) && recommendations.length > 0
    ? recommendations[0]
    : null;

  // Dragging logic
  const handleMouseDown = (e) => {
    if (e.target.closest('.drag-handle')) {
      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y
      });
      e.preventDefault();
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragStart]);

  const getTitle = () => {
    if (recommendationType === 'section') return `Section: ${sectionName || 'N/A'}`;
    if (recommendationType === 'weather') return 'Weather Impact Analysis';
    if (recommendationType === 'pattern') return 'Driver Pattern Analysis';
    if (recommendationType === 'coaching') return 'Coaching Insights';
    return 'AI Recommendation';
  };

  const getIcon = () => {
    if (recommendationType === 'section') return <Psychology />;
    if (recommendationType === 'weather') return <Cloud />;
    if (recommendationType === 'pattern') return <TrendingUp />;
    if (recommendationType === 'coaching') return <School />;
    return <Psychology />;
  };

  if (!recommendationType) return null;

  return (
    <Paper
      ref={panelRef}
      elevation={8}
      sx={{
        position: 'fixed',
        left: position.x,
        top: position.y,
        width: 400,
        maxWidth: '90vw',
        maxHeight: '70vh',
        zIndex: 1300,
        cursor: isDragging ? 'grabbing' : 'default',
        overflow: 'hidden'
      }}
      onMouseDown={handleMouseDown}
    >
      {/* Header */}
      <Box
        className="drag-handle"
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 2,
          bgcolor: 'background.paper',
          borderBottom: 1,
          borderColor: 'divider',
          cursor: 'grab'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {getIcon()}
          <Typography variant="h6" component="h3">
            {getTitle()}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <DragIndicator sx={{ color: 'text.secondary' }} />
          <IconButton size="small" onClick={onClose}>
            <Close />
          </IconButton>
        </Box>
      </Box>

      {/* Content */}
      <Box sx={{ p: 2, maxHeight: 'calc(70vh - 80px)', overflowY: 'auto' }}>
        {loading && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography color="text.secondary">Loading AI analysis...</Typography>
          </Box>
        )}

        {error && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography color="error" gutterBottom>
              Unable to load recommendation
            </Typography>
            <Typography variant="body2" color="text.secondary">
              AI analysis may not be available yet for this data.
            </Typography>
            <Button
              variant="outlined"
              size="small"
              sx={{ mt: 2 }}
              onClick={() => {
                // Just close the panel instead of reloading the page
                if (onClose) {
                  onClose();
                }
              }}
            >
              Close
            </Button>
          </Box>
        )}

        {recommendation && (
          <Box>
            {/* Recommendation Type Chip */}
            <Box sx={{ mb: 2 }}>
              <Chip
                label={`${recommendationType.charAt(0).toUpperCase() + recommendationType.slice(1)} Analysis`}
                color={
                  recommendationType === 'section' ? 'primary' :
                  recommendationType === 'weather' ? 'secondary' :
                  recommendationType === 'coaching' ? 'success' : 'warning'
                }
                size="small"
              />
            </Box>

            <Divider sx={{ mb: 2 }} />

            {/* Coaching Insights Special Rendering */}
            {recommendationType === 'coaching' && recommendation.structured_data && (
              <Box>
                {/* Data Facts */}
                {recommendation.structured_data.data_facts && (
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
                      Key Observations
                    </Typography>
                    {Object.entries(recommendation.structured_data.data_facts).map(([key, value]) => (
                      <Typography key={key} variant="body2" sx={{ mb: 1, pl: 2 }}>
                        <strong>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong> {value}
                      </Typography>
                    ))}
                  </Box>
                )}

                {/* Theories */}
                {recommendation.structured_data.theories && (
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'info.main' }}>
                      Analysis
                    </Typography>
                    {Object.entries(recommendation.structured_data.theories)
                      .filter(([key]) => key !== 'confidence')
                      .map(([key, value]) => (
                        <Typography key={key} variant="body2" sx={{ mb: 1, pl: 2, fontStyle: 'italic' }}>
                          {value}
                        </Typography>
                      ))}
                  </Box>
                )}

                {/* Recommendations - Highlight current section */}
                {recommendation.structured_data.recommendations && (() => {
                  // Filter out empty recommendations (no content)
                  const validRecommendations = recommendation.structured_data.recommendations.filter(rec => {
                    if (!rec || typeof rec !== 'object') return false;
                    // Check if recommendation has any content
                    return !!(rec.focus || rec.action || rec.data_evidence || rec.theory);
                  });
                  
                  if (validRecommendations.length === 0) return null;
                  
                  return (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'success.main' }}>
                        Recommendations
                      </Typography>
                      {validRecommendations.map((rec, idx) => {
                        const focus = rec.focus || '';
                        const isCurrentSection = sectionName && focus.toLowerCase().includes(sectionName.toLowerCase());
                        
                        return (
                          <Box
                            key={idx}
                            sx={{
                              mb: 2,
                              p: 2,
                              borderRadius: 1,
                              border: 1,
                              borderColor: isCurrentSection ? 'success.main' : 'divider',
                              bgcolor: isCurrentSection ? 'rgba(68, 229, 156, 0.08)' : 'background.paper',
                              borderLeft: isCurrentSection ? 4 : 1,
                              borderLeftColor: isCurrentSection ? 'success.main' : 'divider'
                            }}
                          >
                            {isCurrentSection && (
                              <Chip
                                label="Current Section"
                                size="small"
                                color="success"
                                sx={{ mb: 1 }}
                              />
                            )}
                            {rec.priority && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                Priority {rec.priority}
                              </Typography>
                            )}
                            {rec.focus && (
                              <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                                {rec.focus}
                              </Typography>
                            )}
                            {rec.action && (
                              <Typography variant="body2" sx={{ mb: 1 }}>
                                <strong>Action:</strong> {rec.action}
                              </Typography>
                            )}
                            {rec.data_evidence && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontStyle: 'italic' }}>
                                {rec.data_evidence}
                              </Typography>
                            )}
                            {rec.theory && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontStyle: 'italic' }}>
                                {rec.theory}
                              </Typography>
                            )}
                          </Box>
                        );
                      })}
                    </Box>
                  );
                })()}
              </Box>
            )}
            
            {/* Default Rendering for non-coaching types or if structured_data not available */}
            {/* Skip default rendering for weather/pattern - they have custom rendering below */}
            {recommendationType !== 'coaching' && recommendationType !== 'weather' && recommendationType !== 'pattern' && (
              <Box>
                <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.6 }}>
                  {recommendation.recommendation_text || recommendation.analysis_text || 'No recommendation available'}
                </Typography>
              </Box>
            )}

            {/* Structured Data if available (only for non-coaching types) */}
            {recommendationType !== 'coaching' && recommendation.structured_data && (() => {
              const data = recommendation.structured_data;
              
              // Handle Weather Impact data
              if (recommendationType === 'weather') {
                const weatherSummary = recommendation.weather_summary || {};
                const bestPerformer = recommendation.best_performer || {};
                
                return (
                  <Box sx={{ mt: 2 }}>
                    <Divider sx={{ my: 2 }} />
                    
                    {/* ML Analysis Interpretation - Show prominently if available (only if it's actual correlation analysis, not basic summary) */}
                    {recommendation.recommendation_text && 
                     recommendation.recommendation_text.trim() && 
                     !recommendation.recommendation_text.includes("While detailed correlation analysis requires time-aligned lap data") &&
                     !recommendation.recommendation_text.includes("Air temperature averaged") && (
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'info.main' }}>
                          Weather Impact Analysis:
                        </Typography>
                        <Typography variant="body2" sx={{ lineHeight: 1.6, color: 'text.primary' }}>
                          {recommendation.recommendation_text}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, fontStyle: 'italic' }}>
                          Analysis based on all drivers' performance in this race
                        </Typography>
                      </Box>
                    )}
                    
                    {/* Weather Summary from ML Processing */}
                    {(weatherSummary.avg_air_temp_celsius !== undefined || 
                      weatherSummary.avg_humidity_percent !== undefined || 
                      weatherSummary.avg_wind_speed !== undefined) && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                          Weather Conditions:
                        </Typography>
                        {weatherSummary.avg_air_temp_celsius !== undefined && (
                          <Typography variant="body2" sx={{ pl: 2, mb: 0.5 }}>
                            • <strong>Air Temperature:</strong> {Number(weatherSummary.avg_air_temp_celsius).toFixed(1)}°C
                            {weatherSummary.min_air_temp_celsius !== undefined && weatherSummary.max_air_temp_celsius !== undefined && (
                              <span> (range: {Number(weatherSummary.min_air_temp_celsius).toFixed(1)}-{Number(weatherSummary.max_air_temp_celsius).toFixed(1)}°C)</span>
                            )}
                          </Typography>
                        )}
                        {weatherSummary.avg_track_temp_celsius !== undefined && (
                          <Typography variant="body2" sx={{ pl: 2, mb: 0.5 }}>
                            • <strong>Track Temperature:</strong> {Number(weatherSummary.avg_track_temp_celsius).toFixed(1)}°C
                          </Typography>
                        )}
                        {weatherSummary.avg_humidity_percent !== undefined && (
                          <Typography variant="body2" sx={{ pl: 2, mb: 0.5 }}>
                            • <strong>Humidity:</strong> {Number(weatherSummary.avg_humidity_percent).toFixed(1)}%
                          </Typography>
                        )}
                        {weatherSummary.avg_wind_speed !== undefined && (
                          <Typography variant="body2" sx={{ pl: 2, mb: 0.5 }}>
                            • <strong>Wind Speed:</strong> {Number(weatherSummary.avg_wind_speed).toFixed(1)} km/h
                            {weatherSummary.max_wind_speed !== undefined && (
                              <span> (max: {Number(weatherSummary.max_wind_speed).toFixed(1)} km/h)</span>
                            )}
                          </Typography>
                        )}
                        {weatherSummary.rain_detected !== undefined && weatherSummary.rain_detected === false && (
                          <Typography variant="body2" sx={{ pl: 2, mb: 0.5 }}>
                            • <strong>Rain:</strong> No rain detected during the race
                          </Typography>
                        )}
                      </Box>
                    )}
                    
                    {data.data_points !== undefined && (
                      <Typography variant="caption" color="text.secondary">
                        Based on {String(data.data_points)} data points
                      </Typography>
                    )}
                  </Box>
                );
              }
              
              // Handle Driver Pattern data
              if (recommendationType === 'pattern') {
                const trends = recommendation.trends || {};
                const sectionPatterns = recommendation.section_patterns || {};
                const consistencyAnalysis = data.consistency_analysis || {};
                
                return (
                  <Box sx={{ mt: 2 }}>
                    <Divider sx={{ my: 2 }} />
                    
                    {/* Performance Metrics */}
                    <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'warning.main' }}>
                      Performance Metrics:
                    </Typography>
                    
                    {(consistencyAnalysis.lap_count !== undefined || data.lap_count !== undefined) && (
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        <strong>Laps Analyzed:</strong> {String(consistencyAnalysis.lap_count || data.lap_count)}
                      </Typography>
                    )}
                    
                    {(consistencyAnalysis.mean_lap_time_s !== undefined || data.mean_lap_time_s !== undefined) && (
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        <strong>Average Lap Time:</strong> {Number(consistencyAnalysis.mean_lap_time_s || data.mean_lap_time_s).toFixed(3)}s
                      </Typography>
                    )}
                    
                    {(consistencyAnalysis.std_lap_time_s !== undefined || data.std_lap_time_s !== undefined) && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                        <Typography variant="body2">
                          <strong>Consistency (Std Dev):</strong> {Number(consistencyAnalysis.std_lap_time_s || data.std_lap_time_s).toFixed(3)}s
                        </Typography>
                        <MuiTooltip title="Standard deviation of lap times. Lower values indicate more consistent performance. A value of 0.5s means lap times typically vary by ±0.5s from the average." arrow>
                          <InfoOutlined sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
                        </MuiTooltip>
                      </Box>
                    )}
                    
                    {(() => {
                      const score = consistencyAnalysis.consistency_score !== undefined ? consistencyAnalysis.consistency_score : (data.consistency_score !== undefined ? data.consistency_score : undefined);
                      const scoreNum = score !== undefined && score !== null ? Number(score) : NaN;
                      if (!isNaN(scoreNum) && scoreNum >= 0) {
                        return (
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            <strong>Consistency Score:</strong> {(scoreNum * 100).toFixed(1)}%
                          </Typography>
                        );
                      }
                      return null;
                    })()}
                    
                    {((consistencyAnalysis.min_lap_time_s !== undefined && consistencyAnalysis.max_lap_time_s !== undefined) ||
                      (data.min_lap_time_s !== undefined && data.max_lap_time_s !== undefined)) && (
                      <Box sx={{ mb: 2, mt: 1, p: 1.5, bgcolor: 'background.default', borderRadius: 1 }}>
                        <Typography variant="body2" sx={{ mb: 0.5 }}>
                          <strong>Best Lap:</strong> {Number(consistencyAnalysis.min_lap_time_s || data.min_lap_time_s).toFixed(3)}s
                          {(consistencyAnalysis.min_lap_number !== undefined || data.min_lap_number !== undefined) && (
                            <span> (Lap {consistencyAnalysis.min_lap_number || data.min_lap_number})</span>
                          )}
                        </Typography>
                        <Typography variant="body2">
                          <strong>Worst Lap:</strong> {Number(consistencyAnalysis.max_lap_time_s || data.max_lap_time_s).toFixed(3)}s
                          {(consistencyAnalysis.max_lap_number !== undefined || data.max_lap_number !== undefined) && (
                            <span> (Lap {consistencyAnalysis.max_lap_number || data.max_lap_number})</span>
                          )}
                        </Typography>
                        {(consistencyAnalysis.min_lap_time_s || data.min_lap_time_s) && (consistencyAnalysis.max_lap_time_s || data.max_lap_time_s) && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                            Range: {(Number(consistencyAnalysis.max_lap_time_s || data.max_lap_time_s) - Number(consistencyAnalysis.min_lap_time_s || data.min_lap_time_s)).toFixed(3)}s
                          </Typography>
                        )}
                      </Box>
                    )}
                    
                    {/* Trends */}
                    {(trends.consistency_trend || trends.improvement_trend) && (
                      <Box sx={{ mt: 2, mb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'info.main' }}>
                          Trends:
                        </Typography>
                        {trends.consistency_trend && (
                          <Typography variant="body2" sx={{ mb: 1, pl: 2 }}>
                            • <strong>Consistency:</strong> {String(trends.consistency_trend)}
                          </Typography>
                        )}
                        {trends.improvement_trend && (
                          <Typography variant="body2" sx={{ mb: 1, pl: 2, fontStyle: 'italic', color: 'info.main' }}>
                            • <strong>Improvement:</strong> {String(trends.improvement_trend)}
                          </Typography>
                        )}
                      </Box>
                    )}
                    
                    {/* Section Patterns - Strengths */}
                    {sectionPatterns.strengths && Array.isArray(sectionPatterns.strengths) && sectionPatterns.strengths.length > 0 && (
                      <Box sx={{ mt: 2, mb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'success.main' }}>
                          Strengths:
                        </Typography>
                        {sectionPatterns.strengths.map((strength, idx) => (
                          <Typography key={idx} variant="body2" sx={{ mb: 0.5, pl: 2 }}>
                            • {String(strength)}
                          </Typography>
                        ))}
                      </Box>
                    )}
                    
                    {/* Section Patterns - Weaknesses */}
                    {sectionPatterns.weaknesses && Array.isArray(sectionPatterns.weaknesses) && sectionPatterns.weaknesses.length > 0 && (
                      <Box sx={{ mt: 2, mb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'error.main' }}>
                          Areas for Improvement:
                        </Typography>
                        {sectionPatterns.weaknesses.map((weakness, idx) => (
                          <Typography key={idx} variant="body2" sx={{ mb: 0.5, pl: 2 }}>
                            • {String(weakness)}
                          </Typography>
                        ))}
                      </Box>
                    )}
                    
                    {/* Section Analysis Details */}
                    {sectionPatterns.section_analysis && typeof sectionPatterns.section_analysis === 'object' && Object.keys(sectionPatterns.section_analysis).length > 0 && (
                      <Box sx={{ mt: 2, mb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                          Section-by-Section Analysis:
                        </Typography>
                        {Object.entries(sectionPatterns.section_analysis).map(([sectionName, sectionData]) => {
                          if (!sectionData || typeof sectionData !== 'object') return null;
                          const consistency = sectionData.consistency || 'unknown';
                          const consistencyColor = consistency === 'high' ? 'success.main' : consistency === 'moderate' ? 'warning.main' : 'error.main';
                          
                          return (
                            <Box key={sectionName} sx={{ mb: 1.5, pl: 2, borderLeft: 2, borderColor: consistencyColor }}>
                              <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                                {String(sectionName)} ({consistency} consistency)
                              </Typography>
                              {sectionData.mean_time_s !== undefined && (
                                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                  Avg: {Number(sectionData.mean_time_s).toFixed(3)}s
                                  {sectionData.std_time_s !== undefined && ` (std: ${Number(sectionData.std_time_s).toFixed(3)}s)`}
                                  {sectionData.min_time_s !== undefined && sectionData.max_time_s !== undefined && 
                                    ` | Range: ${Number(sectionData.min_time_s).toFixed(3)}-${Number(sectionData.max_time_s).toFixed(3)}s`}
                                </Typography>
                              )}
                            </Box>
                          );
                        })}
                      </Box>
                    )}
                    
                    {/* Consistency Analysis Details */}
                    {consistencyAnalysis.std_lap_time_s !== undefined && (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="caption" color="text.secondary">
                          Consistency analysis based on lap time variance
                        </Typography>
                      </Box>
                    )}
                    
                    {/* Show message if no detailed insights available */}
                    {(!sectionPatterns.strengths || sectionPatterns.strengths.length === 0) && 
                     (!sectionPatterns.weaknesses || sectionPatterns.weaknesses.length === 0) && 
                     (!trends.consistency_trend && !trends.improvement_trend) && (
                      <Box sx={{ mt: 2, p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                          For more detailed coaching insights, check the "Coaching Insights" panel which provides AI-generated analysis with specific recommendations.
                        </Typography>
                      </Box>
                    )}
                  </Box>
                );
              }
              
              // Fallback for other types (shouldn't happen, but safe)
              return null;
            })()}

            {/* Confidence Score */}
            {recommendation.confidence_score && (
              <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
                <Typography variant="caption" color="text.secondary">
                  AI Confidence: {(recommendation.confidence_score * 100).toFixed(1)}%
                </Typography>
              </Box>
            )}
          </Box>
        )}

        {!loading && !error && !recommendation && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography color="text.secondary" gutterBottom>
              No AI analysis available
            </Typography>
            <Typography variant="body2" color="text.secondary">
              ML recommendations are being generated. Please try again in a moment.
            </Typography>
          </Box>
        )}
      </Box>
    </Paper>
  );
};

export default DraggableRecommendationPanel;
