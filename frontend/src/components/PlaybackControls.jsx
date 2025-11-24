import React from 'react';
import { Box, IconButton, Fab, Typography } from '@mui/material';
import { SkipPrevious, SkipNext, PlayArrow, Pause } from '@mui/icons-material';

/**
 * Material 3 Playback Controls for section navigation
 */
function PlaybackControls({ currentSectionIndex, totalSections, onPrevious, onNext, isPlaying, onPlayPause }) {
  return (
    <Box sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 1
    }}>
      {/* Previous Button */}
      <IconButton
        onClick={onPrevious}
        disabled={currentSectionIndex === 0}
        title="Previous Section"
        sx={{
          bgcolor: 'background.paper',
          border: 1,
          borderColor: 'divider',
          '&:hover': {
            bgcolor: 'primary.main',
            borderColor: 'primary.main',
            color: 'primary.contrastText'
          },
          '&:disabled': {
            opacity: 0.5
          }
        }}
      >
        <SkipPrevious />
      </IconButton>

      {/* Play/Pause Floating Action Button (Material 3 Style) */}
      <Fab
        color="primary"
        onClick={onPlayPause}
        title={isPlaying ? "Pause Playback" : "Play Through Circuit"}
        sx={{
          width: 56,
          height: 56,
          boxShadow: 3
        }}
      >
        {isPlaying ? <Pause /> : <PlayArrow />}
      </Fab>

      {/* Next Button */}
      <IconButton
        onClick={onNext}
        disabled={currentSectionIndex >= totalSections - 1}
        title="Next Section"
        sx={{
          bgcolor: 'background.paper',
          border: 1,
          borderColor: 'divider',
          '&:hover': {
            bgcolor: 'primary.main',
            borderColor: 'primary.main',
            color: 'primary.contrastText'
          },
          '&:disabled': {
            opacity: 0.5
          }
        }}
      >
        <SkipNext />
      </IconButton>

      {/* Section Counter */}
      <Typography
        variant="body2"
        sx={{
          fontFamily: 'monospace',
          fontWeight: 700,
          color: 'text.secondary',
          minWidth: '60px',
          textAlign: 'center',
          fontSize: '0.875rem',
          letterSpacing: '0.5px'
        }}
      >
        {totalSections > 0 ? `${currentSectionIndex + 1} / ${totalSections}` : '- / -'}
      </Typography>
    </Box>
  );
}

export default PlaybackControls;