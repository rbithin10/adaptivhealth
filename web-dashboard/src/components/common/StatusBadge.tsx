/* StatusBadge — A small coloured pill that shows a patient's status
   (Stable = green, Warning = amber, Critical = red).
   Converts the AI risk level into a simple visual label. */

// React library
import React from 'react';
import { AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';
import { colors } from '../../theme/colors';

// The risk levels that come from the AI model
export type RiskLevel = 'low' | 'moderate' | 'high';
export type Status = 'stable' | 'warning' | 'critical';

// Convert the AI risk level to a display-friendly status name
export function riskToStatus(riskLevel: RiskLevel | string): Status {
  switch (riskLevel.toLowerCase()) {
    case 'high':
      return 'critical';
    case 'moderate':
      return 'warning';
    case 'low':
    default:
      return 'stable';
  }
}

// Visual settings for each status: colours, labels, and icons
const statusConfig = {
  critical: {
    label: 'Critical',
    bgColor: colors.critical.background,
    textColor: colors.critical.text,
    borderColor: colors.critical.border,
    dotColor: colors.critical.badge,
    icon: AlertTriangle,
  },
  warning: {
    label: 'Warning',
    bgColor: colors.warning.background,
    textColor: colors.warning.text,
    borderColor: colors.warning.border,
    dotColor: colors.warning.badge,
    icon: AlertCircle,
  },
  stable: {
    label: 'Stable',
    bgColor: colors.stable.background,
    textColor: colors.stable.text,
    borderColor: colors.stable.border,
    dotColor: colors.stable.badge,
    icon: CheckCircle,
  },
};

// What this component needs: the status, whether to show an icon, and the size
interface StatusBadgeProps {
  status: Status;
  showIcon?: boolean;
  size?: 'sm' | 'md';
}

// The StatusBadge component — renders a coloured pill with an icon and label
export default function StatusBadge({
  status,
  showIcon = true,
  size = 'md',
}: StatusBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  const paddingSize = size === 'sm' ? '4px 8px' : '6px 12px';
  const fontSize = size === 'sm' ? '11px' : '12px';
  const iconSize = size === 'sm' ? 14 : 16;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: paddingSize,
        borderRadius: '9999px',
        fontSize,
        fontWeight: 500,
        backgroundColor: config.bgColor,
        color: config.textColor,
        border: `1px solid ${config.borderColor}`,
        whiteSpace: 'nowrap',
      }}
    >
      {showIcon && <Icon size={iconSize} strokeWidth={2.5} />}
      {config.label}
    </span>
  );
}
