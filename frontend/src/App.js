import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box, AppBar, Toolbar, Typography, Container } from '@mui/material';
import { Analytics } from '@mui/icons-material';
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import LapReview from './components/LapReview';
import ToyotaIcon from './components/common/ToyotaIcon';

// Material3 Dark Theme for Racing Analysis
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#0091ff', // Racing blue
    },
    secondary: {
      main: '#44e59c', // Performance green
    },
    error: {
      main: '#ff4757', // Alert red
    },
    warning: {
      main: '#ffa800', // Warning orange
    },
    background: {
      default: '#1a1d23', // Dark racing background
      paper: '#242830', // Panel background
    },
    text: {
      primary: '#f0f2f5',
      secondary: '#a0a6b1',
    },
  },
  typography: {
    fontFamily: 'Roboto, sans-serif',
    h1: {
      fontWeight: 700,
      letterSpacing: '0.02em',
    },
    h6: {
      fontWeight: 600,
      letterSpacing: '0.01em',
    },
  },
  shape: {
    borderRadius: 12, // Material3 rounded corners
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarWidth: 'thin',
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#2d323b',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#3a414d',
            borderRadius: '4px',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          boxShadow: '0 6px 20px rgba(0, 0, 0, 0.3)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 8,
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
        <AppBar position="static" elevation={0} sx={{
          bgcolor: 'background.paper',
          borderBottom: '3px solid',
          borderColor: 'primary.main'
        }}>
          <Toolbar>
            <ToyotaIcon sx={{ mr: 2, color: 'primary.main', fontSize: 32 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 700 }}>
              KaizenLap
            </Typography>
            <Analytics sx={{ ml: 2, color: 'text.secondary' }} />
          </Toolbar>
        </AppBar>
        <Container maxWidth={false} disableGutters sx={{ minHeight: 'calc(100vh - 64px)' }}>
          <LapReview />
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;