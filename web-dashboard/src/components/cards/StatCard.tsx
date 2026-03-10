/* StatCard — A small card that shows a single number/stat on the dashboard
   (e.g. "Total Patients: 42" or "Critical: 3") with a coloured accent */

// React library for building the component
import React from 'react';
import { LucideIcon } from 'lucide-react';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';

// The data this card needs: an icon, a label, a number, and a colour theme
interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: number | string;
  color: 'primary' | 'stable' | 'warning' | 'critical';
  onClick?: () => void;
}

// Colour schemes for each card type (primary=blue, stable=green, warning=amber, critical=red)
const colorConfig = {
  primary: {
    borderColor: colors.primary.default,
    backgroundColor: colors.primary.ultralight,
    iconColor: colors.primary.default,
    labelColor: colors.primary.default,
  },
  stable: {
    borderColor: colors.stable.border,
    backgroundColor: colors.stable.background,
    iconColor: colors.stable.badge,
    labelColor: colors.stable.badge,
  },
  warning: {
    borderColor: colors.warning.border,
    backgroundColor: colors.warning.background,
    iconColor: colors.warning.badge,
    labelColor: colors.warning.badge,
  },
  critical: {
    borderColor: colors.critical.border,
    backgroundColor: colors.critical.background,
    iconColor: colors.critical.badge,
    labelColor: colors.critical.badge,
  },
};

// The StatCard component — renders the card with an icon, label, and big number
export default function StatCard({
  icon: Icon,
  label,
  value,
  color,
  onClick,
}: StatCardProps) {
  const config = colorConfig[color];

  return (
    {/* The card container — white box with a subtle shadow */}
    <div
      onClick={onClick}
      style={{
        backgroundColor: colors.neutral.white,
        border: `1px solid ${colors.neutral['300']}`,
        borderRadius: '12px',
        padding: '20px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        position: 'relative',
        overflow: 'hidden',
      }}
      // When hovering: make the shadow bigger and tint the background
      onMouseEnter={(e) => {
        if (onClick) {
          (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 12px rgba(0,0,0,0.12)';
          (e.currentTarget as HTMLDivElement).style.backgroundColor = config.backgroundColor;
        }
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.boxShadow = '0 1px 3px rgba(0,0,0,0.08)';
        (e.currentTarget as HTMLDivElement).style.backgroundColor = colors.neutral.white;
      }}
    >
      {/* Left border accent for colored cards */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: '3px',
          backgroundColor: config.borderColor,
        }}
      />

      {/* Content with left padding to accommodate border accent */}
      <div style={{ paddingLeft: '12px' }}>
        {/* Icon + Label row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '12px',
          }}
        >
          <Icon size={20} color={config.iconColor} strokeWidth={1.5} />
          <span
            style={{
              ...typography.overline,
              color: config.labelColor,
            }}
          >
            {label}
          </span>
        </div>

        {/* Value */}
        <div
          style={{
            fontSize: '36px',
            fontWeight: 700,
            color: colors.neutral['900'],
            lineHeight: '1.0',
          }}
        >
          {value}
        </div>
      </div>
    </div>
  );
}
