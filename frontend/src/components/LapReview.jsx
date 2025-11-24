/**
 * ⚠️ PERFECT UI STATE - DO NOT MODIFY WITHOUT TESTING
 * 
 * This is the main container component with tested, working UI.
 * See DOCS/UI-SPECIFICATIONS.md before making changes.
 * 
 * Critical elements:
 * - trackId resolution: selection?.trackId || selectedTrackId
 * - Best Case Composite race support: ?race_id=${selection.raceId} in endpoints
 * - RecommendationToggle disabled: isComposite || !lapId
 * - compositeType prop passed to DraggableSectionPanel
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Paper, Typography, Alert, CircularProgress,
  Container, Card, CardContent, ButtonGroup, Button,
  Chip, Divider, Stack
} from '@mui/material';
import {
  PlayArrow, Pause, SkipPrevious, SkipNext,
  Analytics, Speed, Cloud, TrendingUp
} from '@mui/icons-material';
import { useApi } from '../hooks/useApi';
import RaceSelector from './RaceSelector';
import InteractiveTrackMap from './InteractiveTrackMap';
import DraggableSectionPanel from './DraggableSectionPanel';
import DraggableRecommendationPanel from './DraggableRecommendationPanel';
import RecommendationToggle from './RecommendationToggle';
import TotalLapTimeComparison from './TotalLapTimeComparison';

const PLAYBACK_SPEED_MS = 2000;

function LapReview() {
  const [selection, setSelection] = useState(null);
  const [trackName, setTrackName] = useState('');
  const [selectedTrackId, setSelectedTrackId] = useState(null);
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeRecommendationType, setActiveRecommendationType] = useState(null); // 'section', 'weather', 'pattern', or null

  const lapId = selection?.lapId;
  const isComposite = selection?.isComposite;
  // Use trackId from selection if available, otherwise use selectedTrackId (for track-only selection)
  const trackId = selection?.trackId || selectedTrackId;
  
  // Use different endpoint for composite vs regular lap
  const sectionsEndpoint = isComposite 
    ? (trackId ? `/api/tracks/${trackId}/best-case/sections${selection?.raceId ? `?race_id=${selection.raceId}` : ''}` : null)
    : (lapId ? `/api/laps/${lapId}/sections` : null);
  
  const { data: lapData, loading, error } = useApi(sectionsEndpoint);
  const sections = lapData?.sections || [];
  const totalDrivers = lapData?.total_drivers || 0;  // For composite mode
  const compositeType = lapData?.composite_type || null;  // 'race' or 'track' for composite mode

  // Fetch Best Case Composite for total lap time comparison (always fetch when we have a track)
  // Also fetch when toggle is on for section-by-section comparison
  const bestCaseEndpoint = trackId && !isComposite
    ? `/api/tracks/${trackId}/best-case${selection?.raceId ? `?race_id=${selection.raceId}` : ''}`
    : null;
  
  const { data: bestCaseData } = useApi(bestCaseEndpoint);
  const bestCaseSections = bestCaseData?.sections || [];
  const bestCaseDict = bestCaseSections.reduce((acc, section) => {
    acc[section.section_name] = section;
    return acc;
  }, {});

  // Reset state when selection changes
  useEffect(() => {
    setCurrentSectionIndex(0);
    setIsPlaying(false);
  }, [selection]);

  // Playback logic
  useEffect(() => {
    let interval;
    if (isPlaying && sections.length > 0) {
      interval = setInterval(() => {
        setCurrentSectionIndex(prevIndex => {
          if (prevIndex >= sections.length - 1) {
            setIsPlaying(false); // Stop at the end
            return prevIndex;
          }
          return prevIndex + 1;
        });
      }, PLAYBACK_SPEED_MS);
    }
    return () => clearInterval(interval);
  }, [isPlaying, sections.length]);

  const handlePlayPause = useCallback(() => {
    if (sections.length === 0) return;
    if (isPlaying) {
      setIsPlaying(false);
    } else {
      // If at the end, restart from the beginning
      if (currentSectionIndex >= sections.length - 1) {
        setCurrentSectionIndex(0);
      }
      setIsPlaying(true);
    }
  }, [isPlaying, sections, currentSectionIndex]);

  const handleStep = useCallback((direction) => {
    setIsPlaying(false);
    setCurrentSectionIndex(prev => {
      const newIndex = prev + direction;
      if (newIndex >= 0 && newIndex < sections.length) {
        return newIndex;
      }
      return prev;
    });
  }, [sections.length]);

  const handleSectionClick = useCallback((sectionName) => {
    const index = sections.findIndex(s => s.section_name === sectionName);
    if (index !== -1) {
      setCurrentSectionIndex(index);
      setIsPlaying(false);
    }
  }, [sections]);

  const currentSection = sections[currentSectionIndex];
  const currentBestCase = currentSection ? bestCaseDict[currentSection.section_name] : null;

  // Get current section's lap_section_id for recommendations
  // The section object from API should have an id field
  const currentLapSectionId = currentSection?.id || null;

  return (
    <Box sx={{ minHeight: '100vh', p: 2 }}>
      <Grid container spacing={3} sx={{ height: 'calc(100vh - 100px)' }}>
        {/* Main Track Map Area */}
        <Grid item xs={12} lg={8}>
          <Card sx={{ height: '100%', position: 'relative', overflow: 'hidden' }}>
            <CardContent sx={{ height: '100%', p: 0, '&:last-child': { pb: 0 } }}>
              <Box sx={{ position: 'relative', height: '100%' }}>
                <InteractiveTrackMap
                  trackId={trackId}
                  currentSectionName={currentSection?.section_name}
                  onSectionClick={handleSectionClick}
                />

                {/* Loading/Error overlays */}
                {loading && (
                  <Box sx={{
                    position: 'absolute',
                    top: 16,
                    left: 16,
                    zIndex: 20,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    bgcolor: 'background.paper',
                    p: 2,
                    borderRadius: 2,
                    boxShadow: 3
                  }}>
                    <CircularProgress size={24} />
                    <Typography>Loading track data...</Typography>
                  </Box>
                )}

                {error && (
                  <Alert
                    severity="error"
                    sx={{
                      position: 'absolute',
                      top: 16,
                      left: 16,
                      zIndex: 20,
                      minWidth: 300
                    }}
                  >
                    {error}
                  </Alert>
                )}

                {!trackId && !loading && (
                  <Box sx={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    zIndex: 20,
                    textAlign: 'center'
                  }}>
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                      Select a Track to Begin
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Choose a track from the control panel to start your analysis
                    </Typography>
                  </Box>
                )}

                {trackId && !lapId && !isComposite && !loading && (
                  <Box sx={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    zIndex: 20,
                    textAlign: 'center'
                  }}>
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                      Select Race & Driver
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Choose a race, driver, and lap to begin performance analysis
                    </Typography>
                  </Box>
                )}

                {/* Section Panel with Playback Controls - Draggable */}
                {lapData && currentSection && (
                  <DraggableSectionPanel
                    section={currentSection}
                    isComposite={isComposite}
                    bestCaseComposite={currentBestCase}
                    totalDrivers={totalDrivers}
                    compositeType={compositeType}
                    currentSectionIndex={currentSectionIndex}
                    totalSections={sections.length}
                    onPrevious={() => handleStep(-1)}
                    onNext={() => handleStep(1)}
                    isPlaying={isPlaying}
                    onPlayPause={handlePlayPause}
                  />
                )}

                {/* Recommendation Panel Overlay */}
                {activeRecommendationType && (
                  <DraggableRecommendationPanel
                    recommendationType={activeRecommendationType}
                    lapSectionId={activeRecommendationType === 'section' ? currentLapSectionId : null}
                    raceId={selection?.raceId}
                    vehicleId={selection?.driverId}
                    sectionName={currentSection?.section_name}
                    onClose={() => setActiveRecommendationType(null)}
                  />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Control Panel */}
        <Grid item xs={12} lg={4}>
          <Stack spacing={3} sx={{ height: '100%', overflow: 'auto' }}>
            {/* AI Analysis Panel */}
            {trackId && (lapId || isComposite) && (
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Analytics sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h6" component="h3">
                      KaizenLap Race AI
                    </Typography>
                  </Box>
                  <RecommendationToggle
                    activeType={activeRecommendationType}
                    onTypeChange={setActiveRecommendationType}
                    disabled={isComposite || !lapId}
                    isComposite={isComposite}
                  />
                </CardContent>
              </Card>
            )}

            {/* Total Lap Time Comparison */}
            {lapData && sections.length > 0 && (
              <TotalLapTimeComparison
                sections={sections}
                bestCaseSections={bestCaseSections}
                isComposite={isComposite}
              />
            )}

            {/* Race Selector */}
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Speed sx={{ mr: 1, color: 'secondary.main' }} />
                  <Typography variant="h6">
                    Race Selection
                  </Typography>
                </Box>
                <RaceSelector
                  onSelectionChange={setSelection}
                  onTrackNameChange={setTrackName}
                  onTrackChange={setSelectedTrackId}
                />
              </CardContent>
            </Card>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}

export default LapReview;