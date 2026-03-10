/* muiTheme.ts — Configures the Material-UI component library to match our brand colours and fonts */

import { createTheme } from '@mui/material/styles';

// Create a custom theme that overrides Material-UI defaults with Adaptiv Health styling
// Always uses light mode — no dark mode toggle
export const theme = createTheme({
  // Colour palette — these are used automatically by MUI buttons, alerts, inputs, etc.
  palette: {
    mode: 'light',             // Force light mode so the dashboard never goes dark
    primary: {
      main: '#2563EB',         // Brand blue for primary buttons and active elements
      dark: '#1E40AF',         // Darker blue for button hover states
      light: '#DBEAFE',        // Light blue for subtle highlights
    },
    error: {
      main: '#EF4444',         // Red for error messages and critical alerts
    },
    warning: {
      main: '#F59E0B',         // Amber for warning messages and moderate risk
    },
    success: {
      main: '#22C55E',         // Green for success messages and healthy status
    },
    background: {
      default: '#F9FAFB',      // Light gray page background
      paper: '#FFFFFF',        // White background for cards, dialogs, and panels
    },
    text: {
      primary: '#111827',      // Near-black text for headings and main content
      secondary: '#6B7280',    // Gray text for less important information
    },
  },
  // Font settings — all MUI components will use Plus Jakarta Sans
  typography: {
    fontFamily: '"Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif',
    h4: {
      fontWeight: 700,         // Make h4 headings bold
    },
    h5: {
      fontWeight: 700,         // Make h5 headings bold
    },
    body2: {
      fontSize: '0.875rem',    // Slightly smaller body text (14px)
    },
  },
});
