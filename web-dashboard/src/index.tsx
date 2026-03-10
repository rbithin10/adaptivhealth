/*
Web app entry point.

This is the very first file that runs when someone opens the dashboard.
It loads the app into the web page and wraps it with our visual theme.
*/

import React from 'react';
import ReactDOM from 'react-dom/client';
// ThemeProvider applies our custom colours and fonts to all Material-UI components
import { ThemeProvider } from '@mui/material/styles';
// CssBaseline resets browser defaults so pages look the same everywhere
import CssBaseline from '@mui/material/CssBaseline';
import './index.css';
import App from './App';
import { theme } from './theme/muiTheme';

// Find the "root" element in the HTML page and mount the entire React app inside it
const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

// Render the app — StrictMode helps catch common mistakes during development
root.render(
  <React.StrictMode>
    {/* Wrap everything in our theme so buttons, text, and colours are consistent */}
    <ThemeProvider theme={theme}>
      {/* CssBaseline removes default browser styles (margins, padding, fonts) */}
      <CssBaseline />
      {/* The main application with all pages and routing */}
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
