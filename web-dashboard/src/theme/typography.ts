// Adaptiv Health Typography Scale
// Plus Jakarta Sans for dashboard (medical-grade, excellent number distinction)
// Reference: Design Guide Part 2.3

export const typography = {
  // Dashboard typography scale
  pageTitle: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#111827',
    lineHeight: '1.2',
  },
  sectionTitle: {
    fontSize: '20px',
    fontWeight: 600,
    color: '#111827',
    lineHeight: '1.3',
  },
  cardTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#111827',
    lineHeight: '1.4',
  },
  body: {
    fontSize: '14px',
    fontWeight: 400,
    color: '#374151',
    lineHeight: '1.5',
  },
  caption: {
    fontSize: '12px',
    fontWeight: 400,
    color: '#6B7280',
    lineHeight: '1.4',
  },
  overline: {
    fontSize: '11px',
    fontWeight: 500,
    color: '#6B7280',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  // Big number displays
  bigNumber: {
    fontSize: '36px',
    fontWeight: 700,
    color: '#111827',
    lineHeight: '1.0',
  },
  bigNumberUnit: {
    fontSize: '16px',
    fontWeight: 400,
    color: '#6B7280',
  },
} as const;
