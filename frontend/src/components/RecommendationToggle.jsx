/**
 * ⚠️ PERFECT UI STATE - DO NOT MODIFY WITHOUT TESTING
 * 
 * This component is part of the tested, working UI.
 * See DOCS/UI-SPECIFICATIONS.md before making changes.
 * 
 * Critical elements:
 * - disabled prop: isComposite || !lapId
 * - isComposite prop: Required for showing explanatory message
 * - Helper message when disabled for Best Case Composite
 */
import React from 'react';
import {
  ToggleButtonGroup, ToggleButton,
  Box, Typography, Chip
} from '@mui/material';
import {
  Psychology, Cloud, TrendingUp, School
} from '@mui/icons-material';

const RecommendationToggle = ({ activeType, onTypeChange, disabled, isComposite }) => {
  const handleTypeChange = (event, newType) => {
    // Prevent any default behavior that might cause page refresh
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (newType !== null) {
      onTypeChange(newType);
    }
  };

  const recommendationTypes = [
    {
      value: 'coaching',
      label: 'Coaching Insights',
      icon: <School sx={{ mr: 1 }} />,
      description: 'Strategic analysis',
      color: 'success'
    },
    {
      value: 'section',
      label: 'Section Analysis',
      icon: <Psychology sx={{ mr: 1 }} />,
      description: 'Corner-specific coaching',
      color: 'primary'
    },
    {
      value: 'weather',
      label: 'Weather Impact',
      icon: <Cloud sx={{ mr: 1 }} />,
      description: 'Track condition analysis',
      color: 'secondary'
    },
    {
      value: 'pattern',
      label: 'Driver Patterns',
      icon: <TrendingUp sx={{ mr: 1 }} />,
      description: 'Consistency insights',
      color: 'warning'
    }
  ];

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 1 }}>
        Select AI Analysis Type:
      </Typography>
      {isComposite && (
        <Box sx={{ mb: 1, p: 1, backgroundColor: 'rgba(128, 128, 128, 0.1)', borderRadius: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
            AI Analysis is not available for Best Case Composite as it combines data from multiple drivers.
          </Typography>
        </Box>
      )}
      <ToggleButtonGroup
        value={activeType}
        exclusive
        onChange={handleTypeChange}
        disabled={disabled}
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 1,
          '& .MuiToggleButton-root': {
            flex: '1 1 auto',
            minWidth: '120px',
            borderRadius: 2,
            py: 1,
            px: 2,
            '&.Mui-selected': {
              backgroundColor: 'primary.main',
              color: 'primary.contrastText',
              '&:hover': {
                backgroundColor: 'primary.dark',
              }
            }
          }
        }}
      >
        {recommendationTypes.map((type) => (
          <ToggleButton
            key={type.value}
            value={type.value}
            disabled={disabled}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', flexDirection: 'column', gap: 0.5 }}>
              {type.icon}
              <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                {type.label}
              </Typography>
            </Box>
          </ToggleButton>
        ))}
      </ToggleButtonGroup>

      {activeType && (
        <Box sx={{ mt: 1 }}>
          <Chip
            label={recommendationTypes.find(t => t.value === activeType)?.description}
            size="small"
            color={recommendationTypes.find(t => t.value === activeType)?.color}
            variant="outlined"
          />
        </Box>
      )}
    </Box>
  );
};

export default RecommendationToggle;
