/* colors.ts — Every colour used across the Adaptiv Health dashboard */
/* These follow medical industry conventions so red = danger, green = safe, yellow = caution */

export const colors = {

  // ---- Brand colours: the main "Adaptiv Health" blue used for buttons, links, etc. ----
  primary: {
    default: '#2563EB',      // Standard blue for buttons and links
    dark: '#1E40AF',         // Darker blue shown when you hover or press a button
    light: '#DBEAFE',        // Light blue used for selected rows and subtle highlights
    ultralight: '#EFF6FF',   // Very faint blue used for card backgrounds on hover
  },

  // ---- Critical / High Risk: red tones indicating danger or urgent attention ----
  critical: {
    background: '#FEF2F2',   // Soft red background for alert cards
    border: '#FCA5A5',       // Red border around critical items
    badge: '#EF4444',        // Bright red for badges and icons
    text: '#991B1B',         // Dark red for readable text on red backgrounds
  },

  // ---- Warning / Moderate Risk: yellow/amber tones indicating caution ----
  warning: {
    background: '#FFFBEB',   // Soft yellow background for warning cards
    border: '#FCD34D',       // Yellow border around warning items
    badge: '#F59E0B',        // Amber for warning badges and icons
    text: '#92400E',         // Dark amber for readable text on yellow backgrounds
  },

  // ---- Stable / Low Risk: green tones indicating everything is healthy ----
  stable: {
    background: '#F0FDF4',   // Soft green background for "all good" cards
    border: '#86EFAC',       // Green border around stable items
    badge: '#22C55E',        // Bright green for healthy-status badges
    text: '#166534',         // Dark green for readable text on green backgrounds
  },

  // ---- Neutral palette: grays used for text, borders, and backgrounds ----
  neutral: {
    '900': '#111827',    // Darkest text — used for main headings and important body text
    '800': '#1F2937',    // Slightly lighter dark text for emphasis
    '700': '#374151',    // Medium-dark text for descriptions and subtitles
    '600': '#4B5563',    // Medium gray for icons and secondary information
    '500': '#6B7280',    // Gray for timestamps, metadata, and tertiary text
    '400': '#9CA3AF',    // Light gray for placeholder text and faded labels
    '300': '#D1D5DB',    // Borders and divider lines between sections
    '200': '#E5E7EB',    // Very light borders and subtle separators
    '100': '#F3F4F6',    // Alternating table row backgrounds and card fills
    '50': '#F9FAFB',     // Page background — the lightest gray
    white: '#FFFFFF',    // Pure white for card surfaces and input fields
  },

  // ---- Chart colours: used in graphs and data visualizations ----
  chart: {
    teal: '#14B8A6',     // Used in health score distribution charts
    blue: '#2563EB',     // Heart rate trend line colour
    success: '#22C55E',  // Positive metric indicators
  },
} as const;
