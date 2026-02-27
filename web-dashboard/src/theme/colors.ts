// Adaptiv Health Color System
// Based on clinical monitoring conventions (ISO 3864 compliant)
// Reference: Design Guide Part 2

export const colors = {
  // Primary brand colors
  primary: {
    default: '#2563EB',      // Buttons, active nav, links, primary actions
    dark: '#1E40AF',         // Hover states, pressed buttons, headers
    light: '#DBEAFE',        // Selected row backgrounds, light badges
    ultralight: '#EFF6FF',   // Page backgrounds, card hover states
  },

  // Clinical status: Critical (High Risk)
  critical: {
    background: '#FEF2F2',
    border: '#FCA5A5',
    badge: '#EF4444',
    text: '#991B1B',
  },

  // Clinical status: Warning (Moderate Risk)
  warning: {
    background: '#FFFBEB',
    border: '#FCD34D',
    badge: '#F59E0B',
    text: '#92400E',
  },

  // Clinical status: Stable (Low Risk)
  stable: {
    background: '#F0FDF4',
    border: '#86EFAC',
    badge: '#22C55E',
    text: '#166534',
  },

  // Neutral palette
  neutral: {
    '900': '#111827',    // Primary text (headings, body text)
    '800': '#1F2937',    // Dark body text, emphasis text
    '700': '#374151',    // Secondary text (descriptions, subtitles)
    '600': '#4B5563',    // Medium gray text, icons
    '500': '#6B7280',    // Tertiary text (timestamps, metadata)
    '400': '#9CA3AF',    // Light gray text, placeholder text
    '300': '#D1D5DB',    // Borders, dividers, disabled states
    '200': '#E5E7EB',    // Light borders, subtle dividers
    '100': '#F3F4F6',    // Card backgrounds, table alternating rows
    '50': '#F9FAFB',     // Page background (dashboard)
    white: '#FFFFFF',    // Card surfaces, input backgrounds
  },

  // Utility colors for charts and data visualization
  chart: {
    teal: '#14B8A6',     // Health score distribution chart
    blue: '#2563EB',     // Heart rate trend
    success: '#22C55E',  // Positive metrics
  },
} as const;
