/* typography.ts — All text size and style presets used across the dashboard */
/* The font "Plus Jakarta Sans" was chosen because numbers look distinct from each other — important for medical data */

export const typography = {

  // Large heading for page titles like "Dashboard" or "Patient List"
  pageTitle: {
    fontSize: '28px',
    fontWeight: 700,       // Bold
    color: '#111827',      // Near-black
    lineHeight: '1.2',
  },

  // Medium heading for sections within a page, like "Recent Alerts"
  sectionTitle: {
    fontSize: '20px',
    fontWeight: 600,       // Semi-bold
    color: '#111827',
    lineHeight: '1.3',
  },

  // Smaller heading used for titles on individual cards
  cardTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#111827',
    lineHeight: '1.4',
  },

  // Standard body text for paragraphs and descriptions
  body: {
    fontSize: '14px',
    fontWeight: 400,       // Normal weight
    color: '#374151',      // Dark gray
    lineHeight: '1.5',
  },

  // Small helper text for timestamps, footnotes, and metadata
  caption: {
    fontSize: '12px',
    fontWeight: 400,
    color: '#6B7280',      // Medium gray
    lineHeight: '1.4',
  },

  // Tiny uppercase label used above metrics (e.g. "HEART RATE")
  overline: {
    fontSize: '11px',
    fontWeight: 500,
    color: '#6B7280',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },

  // Extra-large number for displaying vitals like "92" (heart rate)
  bigNumber: {
    fontSize: '36px',
    fontWeight: 700,
    color: '#111827',
    lineHeight: '1.0',
  },

  // The unit label next to a big number, like "BPM" beside the heart rate
  bigNumberUnit: {
    fontSize: '16px',
    fontWeight: 400,
    color: '#6B7280',
  },
} as const;
