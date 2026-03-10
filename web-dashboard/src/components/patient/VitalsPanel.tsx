/* VitalsPanel — Displays a patient's current vital signs (heart rate, SpO2, blood pressure)
   as cards, plus a line chart showing their vitals history over time. */

import React from 'react';
// Icons for each vital sign type
import { Heart, Wind, Activity, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { RiskAssessmentResponse, VitalSignResponse, VitalSignsHistoryResponse } from '../../types';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';

// What this panel needs: vital sign data, history, time range, and status helpers
interface VitalsPanelProps {
  latestVitals: VitalSignResponse | null;
  vitalsHistory: VitalSignsHistoryResponse | null;
  timeRange: '1week' | '2weeks' | '1month' | '3months';
  setTimeRange: React.Dispatch<React.SetStateAction<'1week' | '2weeks' | '1month' | '3months'>>;
  riskAssessment: RiskAssessmentResponse | null;
  computingRisk: boolean;
  onComputeRisk: () => void;
  getVitalStatus: (value: number, type: 'hr' | 'spo2' | 'bp') => 'stable' | 'warning' | 'critical';
}

// The vitals display component with live readings and historical chart
const VitalsPanel: React.FC<VitalsPanelProps> = ({
  latestVitals,
  vitalsHistory,
  timeRange,
  setTimeRange,
  riskAssessment,
  computingRisk,
  onComputeRisk,
  getVitalStatus,
}) => {
  const vitalsAny = latestVitals as (VitalSignResponse & {
    blood_pressure_systolic?: number;
    blood_pressure_diastolic?: number;
  }) | null;

  const systolic = vitalsAny?.blood_pressure?.systolic ?? vitalsAny?.blood_pressure_systolic ?? 0;
  const diastolic = vitalsAny?.blood_pressure?.diastolic ?? vitalsAny?.blood_pressure_diastolic ?? 0;
  const heartRate = latestVitals?.heart_rate ?? null;
  const spo2Value = latestVitals?.spo2 ?? null;

  return (
    <>
      <h2 style={{ ...typography.sectionTitle, marginBottom: '16px' }}>Current Vitals</h2>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '32px',
        }}
      >
        <div style={{ backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`, borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Heart size={20} color={colors.critical.badge} />
            <span style={typography.overline}>Heart Rate</span>
          </div>
          <div style={{ ...typography.bigNumber, marginBottom: '4px' }}>{heartRate ?? '--'}</div>
          <div style={typography.bigNumberUnit}>{heartRate != null ? 'BPM' : ''}</div>
          <div style={{ ...typography.caption, marginTop: '8px', color: heartRate == null ? colors.neutral['500'] : getVitalStatus(heartRate, 'hr') === 'critical' ? colors.critical.text : getVitalStatus(heartRate, 'hr') === 'warning' ? colors.warning.text : colors.stable.text }}>
            {heartRate == null ? 'No data' : '↑ High'}
          </div>
        </div>

        <div style={{ backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`, borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Wind size={20} color={colors.critical.badge} />
            <span style={typography.overline}>SpO2</span>
          </div>
          <div style={{ ...typography.bigNumber, marginBottom: '4px' }}>{spo2Value != null ? `${spo2Value.toFixed(0)}%` : '--'}</div>
          <div style={{ ...typography.caption, marginTop: '8px', color: spo2Value == null ? colors.neutral['500'] : spo2Value < 90 ? colors.critical.text : colors.warning.text }}>
            {spo2Value == null ? 'No data' : '↓ Low'}
          </div>
        </div>

        <div style={{ backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`, borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Activity size={20} color={colors.critical.badge} />
            <span style={typography.overline}>Blood Pressure</span>
          </div>
          <div style={{ ...typography.bigNumber, marginBottom: '4px' }}>{systolic || '--'}/{diastolic || '--'}</div>
          <div style={{ ...typography.caption, marginTop: '8px', color: systolic === 0 ? colors.neutral['500'] : getVitalStatus(systolic, 'bp') === 'critical' ? colors.critical.text : getVitalStatus(systolic, 'bp') === 'warning' ? colors.warning.text : colors.stable.text }}>
            {systolic === 0 ? 'No data' : '↑ High'}
          </div>
        </div>

        <div style={{ backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`, borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <AlertTriangle size={20} color={colors.critical.badge} />
            <span style={typography.overline}>Risk Level</span>
          </div>
          {riskAssessment ? (
            <>
              <div style={{ ...typography.bigNumber, marginBottom: '4px', color: colors.critical.badge }}>
                {riskAssessment.risk_level?.toUpperCase()}
              </div>
              <div style={{ ...typography.body, color: colors.neutral['700'] }}>{riskAssessment.risk_score.toFixed(2)}</div>
            </>
          ) : (
            <button
              onClick={onComputeRisk}
              disabled={computingRisk}
              style={{ marginTop: '4px', padding: '8px 12px', backgroundColor: colors.primary.default, color: colors.neutral.white, border: 'none', borderRadius: '6px', cursor: computingRisk ? 'not-allowed' : 'pointer', fontSize: '12px', fontWeight: 500, opacity: computingRisk ? 0.7 : 1, width: '100%' }}
            >
              {computingRisk ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><RefreshCw size={14} /> Computing...</span>
              ) : (
                'Run AI Assessment'
              )}
            </button>
          )}
        </div>
      </div>

      <div style={{ marginBottom: '32px', display: 'flex', gap: '8px' }}>
        {['1week', '2weeks', '1month', '3months'].map((range) => (
          <button
            key={range}
            onClick={() => setTimeRange(range as '1week' | '2weeks' | '1month' | '3months')}
            style={{ padding: '8px 16px', borderRadius: '6px', border: 'none', backgroundColor: timeRange === range ? colors.primary.default : colors.neutral['100'], color: timeRange === range ? colors.neutral.white : colors.neutral['700'], cursor: 'pointer', fontWeight: 500, transition: 'all 0.2s' }}
          >
            {range === '1week' && '1 Week'}
            {range === '2weeks' && '2 Weeks'}
            {range === '1month' && '1 Month'}
            {range === '3months' && '3 Months'}
          </button>
        ))}
      </div>

      <div style={{ backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`, borderRadius: '12px', padding: '24px', marginBottom: '32px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <h3 style={{ ...typography.sectionTitle, marginBottom: '16px' }}>Heart Rate History</h3>
        {vitalsHistory?.vitals?.length ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={vitalsHistory.vitals.map((v) => ({
              time: new Date(v.timestamp).toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                hour12: true,
              }),
              hr: v.heart_rate,
              spo2: v.spo2,
              systolic: v.blood_pressure?.systolic || null,
              timestamp: v.timestamp,
            }))}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.neutral['300']} />
              <XAxis dataKey="time" stroke={colors.neutral['500']} style={{ fontSize: '12px' }} />
              <YAxis stroke={colors.neutral['500']} style={{ fontSize: '12px' }} domain={[40, 180]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: colors.neutral.white,
                  border: `1px solid ${colors.neutral['300']}`,
                  borderRadius: '6px',
                }}
                formatter={(value) => {
                  if (value === null || value === undefined) return 'N/A';
                  const n = typeof value === 'number' ? value : Number(value);
                  return Number.isFinite(n) ? n.toFixed(1) : 'N/A';
                }}
              />
              <Legend wrapperStyle={{ paddingTop: '16px' }} />
              <Line type="monotone" dataKey="hr" stroke={colors.critical.badge} name="Heart Rate (BPM)" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="spo2" stroke={colors.warning.badge} name="SpO2 (%)" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: colors.neutral['50'], borderRadius: '8px', color: colors.neutral['500'] }}>
            No vitals history available for chart
          </div>
        )}
      </div>
    </>
  );
};

export default VitalsPanel;
