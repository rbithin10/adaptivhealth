/* AdvancedMLPanel — A collapsible panel that shows AI anomaly detection results.
   If anomalies were found, the header turns amber as a visual warning. */

import React from 'react';
import { ChevronDown, ChevronUp, Radar } from 'lucide-react';
import {
  AnomalyDetectionResponse,
} from '../../types';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';

// What this panel needs: anomaly data, whether it's open, and its child content
interface AdvancedMLPanelProps {
  anomalyData: AnomalyDetectionResponse | null;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

// The collapsible ML panel component
const AdvancedMLPanel: React.FC<AdvancedMLPanelProps> = ({
  anomalyData,
  expanded,
  onToggle,
  children,
}) => {
  return (
    <div
      style={{
        backgroundColor: colors.neutral.white,
        border: `1px solid ${colors.neutral['300']}`,
        borderRadius: '12px',
        marginBottom: '24px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        overflow: 'hidden',
      }}
    >
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '20px 24px',
          backgroundColor: anomalyData && anomalyData.anomaly_count > 0
            ? colors.warning.background
            : colors.neutral.white,
          border: 'none',
          cursor: 'pointer',
          borderBottom: expanded ? `1px solid ${colors.neutral['300']}` : 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Radar
            size={22}
            color={anomalyData && anomalyData.anomaly_count > 0 ? colors.warning.text : colors.primary.default}
          />
          <span style={{ ...typography.sectionTitle, margin: 0 }}>Anomaly Detection</span>
          {anomalyData && anomalyData.anomaly_count > 0 && (
            <span
              style={{
                backgroundColor: colors.warning.badge,
                color: colors.neutral.white,
                fontSize: '12px',
                fontWeight: 700,
                padding: '2px 10px',
                borderRadius: '12px',
              }}
            >
              {anomalyData.anomaly_count} found
            </span>
          )}
          {anomalyData && anomalyData.status === 'normal' && (
            <span
              style={{
                backgroundColor: colors.stable.badge,
                color: colors.neutral.white,
                fontSize: '12px',
                fontWeight: 700,
                padding: '2px 10px',
                borderRadius: '12px',
              }}
            >
              All normal
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp size={20} color={colors.neutral['500']} />
        ) : (
          <ChevronDown size={20} color={colors.neutral['500']} />
        )}
      </button>

      {expanded && children}
    </div>
  );
};

export default AdvancedMLPanel;
