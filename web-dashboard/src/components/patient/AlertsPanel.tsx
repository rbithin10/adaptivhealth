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

type AlertStatusFilter = 'all' | 'active' | 'acknowledged' | 'resolved';

// The alerts list component — shows each alert with Acknowledge and Resolve buttons
const AlertsPanel: React.FC<AlertsPanelProps> = ({ alerts, formatTimeAgo, onAcknowledgeAlert, onResolveAlert }) => {
  const [severityFilter, setSeverityFilter] = React.useState<string>('all');
  const [statusFilter, setStatusFilter] = React.useState<AlertStatusFilter>('all');
  const [typeFilter, setTypeFilter] = React.useState<string>('all');

  const availableTypes = React.useMemo(() => {
    const allTypes = alerts.map((alert) => alert.alert_type).filter(Boolean);
    return Array.from(new Set(allTypes)).sort();
  }, [alerts]);

  const filteredAlerts = React.useMemo(() => {
    return alerts.filter((alert) => {
      if (severityFilter !== 'all' && alert.severity !== severityFilter) {
        return false;
      }

      if (typeFilter !== 'all' && alert.alert_type !== typeFilter) {
        return false;
      }

      if (statusFilter === 'active') {
        return !alert.resolved_at;
      }
      if (statusFilter === 'acknowledged') {
        return Boolean(alert.acknowledged);
      }
      if (statusFilter === 'resolved') {
        return Boolean(alert.resolved_at);
      }

      return true;
    });
  }, [alerts, severityFilter, statusFilter, typeFilter]);

  const resetFilters = () => {
    setSeverityFilter('all');
    setStatusFilter('all');
    setTypeFilter('all');
  };

  return (
    <div style={{ backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`, borderRadius: '12px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
      <h3 style={{ ...typography.sectionTitle, marginBottom: '12px' }}>Alert History</h3>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px', marginBottom: '12px' }}>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          style={{ width: '100%', minWidth: 0, padding: '8px', borderRadius: '8px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
        >
          <option value="all">All Severities</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
          <option value="emergency">Emergency</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as AlertStatusFilter)}
          style={{ width: '100%', minWidth: 0, padding: '8px', borderRadius: '8px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
        >
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={{ width: '100%', minWidth: 0, padding: '8px', borderRadius: '8px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
        >
          <option value="all">All Types</option>
          {availableTypes.map((typeValue) => (
            <option key={typeValue} value={typeValue}>
              {String(typeValue).replaceAll('_', ' ')}
            </option>
          ))}
        </select>

        <button
          onClick={resetFilters}
          style={{
            width: '100%',
            minWidth: 0,
            padding: '8px 12px',
            borderRadius: '8px',
            border: `1px solid ${colors.neutral['300']}`,
            backgroundColor: colors.neutral.white,
            color: colors.neutral['800'],
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Reset
        </button>
      </div>

      <div style={{ ...typography.caption, marginBottom: '12px' }}>
        Showing {filteredAlerts.length} of {alerts.length} alerts
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '360px', overflowY: 'scroll', paddingRight: '4px' }}>
        {filteredAlerts.length === 0 ? (
          <div style={{ padding: '12px', backgroundColor: colors.neutral['50'], borderRadius: '8px' }}>
            <div style={{ ...typography.body, fontWeight: 600 }}>
              {alerts.length === 0 ? 'No alerts available' : 'No alerts match the selected filters'}
            </div>
          </div>
        ) : (
          filteredAlerts.map((alert) => {
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
                <div style={{ ...typography.caption, color: text, marginTop: '-4px', marginBottom: '8px', opacity: 0.85 }}>
                  {new Date(alert.created_at).toLocaleString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZoneName: 'short',
                  })}
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
