/* AlertsPanel — Shows a list of health alerts for a patient.
   Each alert can be acknowledged or resolved by the clinician. */

import React from 'react';
// Data shape for a single alert
import { AlertResponse } from '../../types';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';

// What this panel needs: the patient's alerts and action handlers
interface AlertsPanelProps {
  patientId: number;
  alerts: AlertResponse[];
  formatTimeAgo: (isoDate?: string) => string;
  onAcknowledgeAlert: (alertId: number) => Promise<void>;
  onResolveAlert: (alertId: number) => Promise<void>;
}

// The alerts list component — shows each alert with Acknowledge and Resolve buttons
const AlertsPanel: React.FC<AlertsPanelProps> = ({ alerts, formatTimeAgo, onAcknowledgeAlert, onResolveAlert }) => {
  return (
    <div style={{ backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`, borderRadius: '12px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
      <h3 style={{ ...typography.sectionTitle, marginBottom: '16px' }}>Alert History</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {alerts.length === 0 ? (
          <div style={{ padding: '12px', backgroundColor: colors.neutral['50'], borderRadius: '8px' }}>
            <div style={{ ...typography.body, fontWeight: 600 }}>No alerts available</div>
          </div>
        ) : (
          alerts.map((alert) => {
            const isCritical = alert.severity === 'critical' || alert.severity === 'emergency';
            const bg = isCritical ? colors.critical.background : colors.warning.background;
            const text = isCritical ? colors.critical.text : colors.warning.text;
            return (
              <div key={alert.alert_id} style={{ padding: '12px', backgroundColor: bg, borderRadius: '8px' }}>
                <div style={{ ...typography.body, color: text, fontWeight: 600 }}>
                  ● {alert.severity.toUpperCase()}: {alert.title || alert.alert_type.replaceAll('_', ' ')}
                </div>
                <div style={{ ...typography.caption, color: text, marginTop: '4px', marginBottom: '8px' }}>
                  {formatTimeAgo(alert.created_at)}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {!alert.acknowledged && (
                    <button
                      onClick={() => onAcknowledgeAlert(alert.alert_id)}
                      style={{
                        padding: '6px 10px',
                        borderRadius: '6px',
                        border: 'none',
                        backgroundColor: colors.primary.default,
                        color: colors.neutral.white,
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: '12px',
                      }}
                    >
                      Acknowledge
                    </button>
                  )}
                  {!alert.resolved_at && (
                    <button
                      onClick={() => onResolveAlert(alert.alert_id)}
                      style={{
                        padding: '6px 10px',
                        borderRadius: '6px',
                        border: 'none',
                        backgroundColor: colors.stable.badge,
                        color: colors.neutral.white,
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: '12px',
                      }}
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default AlertsPanel;
