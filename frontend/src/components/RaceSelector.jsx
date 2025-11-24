/**
 * ⚠️ PERFECT UI STATE - DO NOT MODIFY WITHOUT TESTING
 * 
 * This component is part of the tested, working UI.
 * See DOCS/UI-SPECIFICATIONS.md before making changes.
 * 
 * Critical elements:
 * - onSelectionChange(null) calls in handleTrackChange and handleRaceChange
 * - These calls ensure immediate map updates when track/race changes
 * - DO NOT REMOVE these null assignments
 */
import React, { useState, useEffect } from 'react';
import {
  FormControl, InputLabel, Select, MenuItem,
  FormControlLabel, Switch, Box, Stack,
  CircularProgress, Typography
} from '@mui/material';
import { useApi } from '../hooks/useApi';

function RaceSelector({ onSelectionChange, onTrackNameChange, onTrackChange }) {
  const [selectedTrack, setSelectedTrack] = useState('');
  const [selectedRace, setSelectedRace] = useState('');
  const [selectedDriver, setSelectedDriver] = useState('');
  const [selectedLap, setSelectedLap] = useState('');
  const [isComposite, setIsComposite] = useState(false);

  // Fetch tracks
  const { data: tracks, loading: tracksLoading, error: tracksError } = useApi('/api/tracks');
  
  // Fetch races for selected track
  const { data: races, loading: racesLoading, error: racesError } = useApi(selectedTrack ? `/api/tracks/${selectedTrack}/races` : null);
  
  // Fetch race context (all data in one request) when race is selected
  const { data: raceContext, loading: contextLoading, error: contextError } = useApi(selectedRace ? `/api/races/${selectedRace}/context` : null);

  // Handle cascading resets
  const handleTrackChange = (e) => {
    const newTrackId = e.target.value;
    console.log('Track changed to:', newTrackId);
    setSelectedTrack(newTrackId);
    setSelectedRace('');
    setSelectedDriver('');
    setSelectedLap('');
    setIsComposite(false);
    
    // Clear selection immediately when track changes
    if (onSelectionChange) {
      onSelectionChange(null);
    }
    
    // Notify parent immediately when track is selected
    if (onTrackChange && newTrackId) {
      onTrackChange(newTrackId);
      const trackName = tracks?.find(t => t.id === parseInt(newTrackId))?.name;
      if (trackName && onTrackNameChange) {
        onTrackNameChange(trackName);
      }
    } else if (onTrackChange && !newTrackId) {
      // Track deselected
      onTrackChange(null);
      if (onTrackNameChange) {
        onTrackNameChange('');
      }
    }
  };

  const handleRaceChange = (e) => {
    setSelectedRace(e.target.value);
    setSelectedDriver('');
    setSelectedLap('');
    setIsComposite(false);
    
    // Clear selection when race changes
    if (onSelectionChange) {
      onSelectionChange(null);
    }
  };

  const handleDriverChange = (e) => {
    const value = e.target.value;
    if (value === 'composite') {
      setIsComposite(true);
      setSelectedDriver('');
      setSelectedLap('');
    } else {
      setIsComposite(false);
      setSelectedDriver(value);
      setSelectedLap('');
      
      // Immediately clear composite selection when switching to regular driver
      if (onSelectionChange) {
        onSelectionChange(null);
      }
    }
  };
  
  // Notify parent of the final, complete selection
  useEffect(() => {
    if (isComposite && selectedTrack) {
      // Composite racer selection - can now include race if selected
      onSelectionChange({
        trackId: selectedTrack,
        raceId: selectedRace || null,
        driverId: null,
        lapId: null,
        isComposite: true,
      });
      
      const trackName = tracks?.find(t => t.id === parseInt(selectedTrack))?.name;
      if (trackName) {
        onTrackNameChange(trackName);
      }
    } else if (selectedTrack && selectedRace && selectedDriver && selectedLap) {
      // Regular lap selection
      const selectedDriverData = raceContext?.drivers?.find(d => d.id === parseInt(selectedDriver));
      const selectedLapData = selectedDriverData?.laps?.find(l => l.id === selectedLap);
      
      onSelectionChange({
        trackId: selectedTrack,
        raceId: selectedRace,
        driverId: selectedDriver,
        lapId: selectedLap,  // Keep as string (composite key: "race_id|vehicle_id|lap_number")
        lapNumber: selectedLapData?.lap_number,
        isComposite: false,
      });
      
      const trackName = raceContext?.track?.name || tracks?.find(t => t.id === parseInt(selectedTrack))?.name;
      if (trackName) {
        onTrackNameChange(trackName);
      }
    }
  }, [selectedTrack, selectedRace, selectedDriver, selectedLap, isComposite, raceContext, tracks, onSelectionChange, onTrackNameChange]);
  
  const handleLapChange = (e) => {
    const lapId = e.target.value;
    setSelectedLap(lapId);
  };
  
  // Get drivers and laps from race context
  const drivers = raceContext?.drivers || [];
  const selectedDriverData = drivers.find(d => d.id === parseInt(selectedDriver));
  const laps = selectedDriverData?.laps || [];
  
  return (
    <Stack spacing={2}>
      {/* Track Selection */}
      <FormControl fullWidth>
        <InputLabel>Track</InputLabel>
        <Select
          value={selectedTrack}
          onChange={handleTrackChange}
          disabled={tracksLoading || !tracks || tracks.length === 0}
          label="Track"
        >
          <MenuItem value="">
            <em>{tracksLoading ? 'Loading...' : (tracks && tracks.length > 0 ? 'Select Track' : 'No tracks available')}</em>
          </MenuItem>
          {tracks && tracks.length > 0 && tracks.map(track => (
            <MenuItem key={track.id} value={String(track.id)}>
              {track.name}
            </MenuItem>
          ))}
        </Select>
        {tracksLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
            <CircularProgress size={20} />
          </Box>
        )}
      </FormControl>

      {/* Race Selection */}
      <FormControl fullWidth disabled={!selectedTrack}>
        <InputLabel>Race</InputLabel>
        <Select
          value={selectedRace}
          onChange={handleRaceChange}
          disabled={!selectedTrack || racesLoading}
          label="Race"
        >
          <MenuItem value="">
            <em>{racesLoading ? 'Loading...' : 'Select Race (or use Best Case Composite)'}</em>
          </MenuItem>
          {races?.map(race => (
            <MenuItem key={race.id} value={race.id}>
              Race {race.race_number}
            </MenuItem>
          ))}
        </Select>
        {racesLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
            <CircularProgress size={20} />
          </Box>
        )}
      </FormControl>

      {/* Driver Selection - Enabled after Race selection OR for Best Case Composite (track only) */}
      <FormControl fullWidth disabled={!selectedTrack}>
        <InputLabel>Driver</InputLabel>
        <Select
          value={isComposite ? 'composite' : selectedDriver}
          onChange={handleDriverChange}
          disabled={!selectedTrack || contextLoading}
          label="Driver"
        >
          <MenuItem value="">
            <em>{contextLoading ? 'Loading...' : 'Select Driver'}</em>
          </MenuItem>
          {selectedTrack && (
            <MenuItem value="composite">🏆 Best Case Composite (All Drivers)</MenuItem>
          )}
          {selectedRace && drivers.map(driver => (
            <MenuItem key={driver.id} value={driver.id}>
              {driver.car_number || driver.vehicle_id || driver.id}
            </MenuItem>
          ))}
          {!selectedRace && selectedTrack && !isComposite && (
            <MenuItem disabled>
              <em>Select a race to view individual drivers</em>
            </MenuItem>
          )}
        </Select>
        {contextLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
            <CircularProgress size={20} />
          </Box>
        )}
      </FormControl>

      {/* Lap Selection */}
      {!isComposite && (
        <FormControl fullWidth disabled={!selectedDriver}>
          <InputLabel>Lap</InputLabel>
          <Select
            value={selectedLap}
            onChange={handleLapChange}
            disabled={!selectedDriver || laps.length === 0}
            label="Lap"
          >
            <MenuItem value="">
              <em>{laps.length === 0 ? 'No laps available' : 'Select Lap'}</em>
            </MenuItem>
            {laps.map(lap => (
              <MenuItem key={lap.id} value={lap.id}>
                Lap {lap.lap_number} ({(lap.lap_time_ms / 1000).toFixed(3)}s)
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
    </Stack>
  );
}

export default RaceSelector;