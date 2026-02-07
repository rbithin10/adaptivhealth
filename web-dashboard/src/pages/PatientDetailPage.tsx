/*
Patient detail page.

Shows detailed information about one patient:
- Current vital signs and risk score
- Historical trends over time
- Recent alerts
- AI recommendations
*/

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Heart, Wind, Activity, AlertTriangle, Calendar } from 'lucide-react';
import { api, User } from '../services/api';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';
import StatusBadge, { riskToStatus } from '../components/common/StatusBadge';

interface VitalReading {
  id: number;
  heart_rate: number;
  spo2: number;
  systolic_bp: number;
  diastolic_bp: number;
  timestamp: string;
}

interface RiskAssessment {
  risk_level: string;
  risk_score: number;
  contributing_factors: string[];
  recommendation: string;
}

const PatientDetailPage: React.FC = () => {
  const { patientId } = useParams<{ patientId: string }>();
  const navigate = useNavigate();
  const [patient, setPatient] = useState<User | null>(null);
  const [latestVitals, setLatestVitals] = useState<VitalReading | null>(null);
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(null);
  const [timeRange, setTimeRange] = useState<'1week' | '2weeks' | '1month' | '3months'>('1week');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPatientData();
  }, [patientId]);

  const loadPatientData = async () => {
    try {
      // Fetch actual patient data from the API
      const user = patientId
        ? await api.getUserById(patientId)
        : await api.getCurrentUser();
      setPatient(user);

      // Fetch real vitals from the backend
      try {
        const vitals = await api.getVitalSigns(patientId);
        if (Array.isArray(vitals) && vitals.length > 0) {
          const latest = vitals[0];
          setLatestVitals({
            id: Number(latest.vital_id ?? 1),
            heart_rate: latest.heart_rate,
            spo2: latest.spo2 ?? 98,
            systolic_bp: latest.systolic_bp ?? 120,
            diastolic_bp: latest.diastolic_bp ?? 80,
            timestamp: latest.timestamp,
          });
        } else {
          // No vitals data available yet
          setLatestVitals({
            id: 0,
            heart_rate: 72,
            spo2: 98,
            systolic_bp: 120,
            diastolic_bp: 80,
            timestamp: new Date().toISOString(),
          });
        }
      } catch {
        // Fallback if vitals endpoint is unavailable
        setLatestVitals({
          id: 0,
          heart_rate: 72,
          spo2: 98,
          systolic_bp: 120,
          diastolic_bp: 80,
          timestamp: new Date().toISOString(),
        });
      }

      // Fetch real risk assessment
      try {
        const riskData = await api.getRiskAssessments(patientId);
        if (riskData && Array.isArray((riskData as any)?.risk_assessments) && (riskData as any).risk_assessments.length > 0) {
          const latest = (riskData as any).risk_assessments[0];
          setRiskAssessment({
            risk_level: latest.risk_level || 'low',
            risk_score: latest.risk_score || 0.0,
            contributing_factors: latest.primary_concern ? [latest.primary_concern] : [],
            recommendation: latest.recommendation || 'Continue normal activities',
          });
        } else {
          setRiskAssessment({
            risk_level: 'low',
            risk_score: 0.0,
            contributing_factors: [],
            recommendation: 'No risk assessments available yet',
          });
        }
      } catch {
        setRiskAssessment({
          risk_level: 'low',
          risk_score: 0.0,
          contributing_factors: [],
          recommendation: 'Risk assessment unavailable',
        });
      }
    } catch (error) {
      console.error('Error loading patient data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '32px', textAlign: 'center' }}>
        <p>Loading patient data...</p>
      </div>
    );
  }

  if (!patient || !latestVitals) {
    return (
      <div style={{ padding: '32px' }}>
        <p>Patient data not found</p>
      </div>
    );
  }

  // Helper function to get vital status
  const getVitalStatus = (value: number, type: 'hr' | 'spo2' | 'bp'): 'stable' | 'warning' | 'critical' => {
    if (type === 'hr') {
      if (value > 130) return 'critical';
      if (value > 110) return 'warning';
      return 'stable';
    }
    if (type === 'spo2') {
      if (value < 90) return 'critical';
      if (value < 95) return 'warning';
      return 'stable';
    }
    if (type === 'bp') {
      if (value > 140) return 'critical';
      if (value > 130) return 'warning';
      return 'stable';
    }
    return 'stable';
  };

  const riskStatus = riskToStatus(riskAssessment?.risk_level || 'low');

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.neutral['50'] }}>
      {/* Header */}
      <header
        style={{
          backgroundColor: colors.neutral.white,
          borderBottom: `1px solid ${colors.neutral['300']}`,
          padding: '16px 32px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={() => navigate('/patients')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: colors.primary.default,
              fontWeight: 500,
            }}
          >
            <ArrowLeft size={20} />
            Back to Patients
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: '1440px', margin: '0 auto', padding: '32px' }}>
        {/* Patient Header */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            padding: '24px',
            marginBottom: '32px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '24px' }}>
            {/* Avatar */}
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                backgroundColor: colors.primary.light,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                fontSize: '24px',
                fontWeight: 700,
                color: colors.primary.default,
              }}
            >
              {patient.name?.substring(0, 2).toUpperCase()}
            </div>

            {/* Patient Info */}
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
                <h1 style={{ ...typography.sectionTitle, margin: 0 }}>{patient.name}</h1>
                <StatusBadge status={riskStatus} />
              </div>
              <p style={{ ...typography.body, margin: '4px 0' }}>
                {patient.gender?.charAt(0).toUpperCase()}{patient.gender?.slice(1) || 'N/A'}, {patient.age} years old
              </p>
              <p style={{ ...typography.caption, margin: '4px 0' }}>
                Last reading: {new Date(latestVitals.timestamp).getMinutes()} min ago
              </p>
              <p style={{ ...typography.caption, margin: '4px 0' }}>Device: Fitbit Charge 6</p>
            </div>
          </div>
        </div>

        {/* Current Vitals Grid */}
        <h2 style={{ ...typography.sectionTitle, marginBottom: '16px' }}>Current Vitals</h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
            marginBottom: '32px',
          }}
        >
          {/* Heart Rate */}
          <div
            style={{
              backgroundColor: colors.neutral.white,
              border: `1px solid ${colors.neutral['300']}`,
              borderRadius: '12px',
              padding: '20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Heart size={20} color={colors.critical.badge} />
              <span style={typography.overline}>Heart Rate</span>
            </div>
            <div style={{ ...typography.bigNumber, marginBottom: '4px' }}>
              {latestVitals.heart_rate}
            </div>
            <div style={typography.bigNumberUnit}>BPM</div>
            <div
              style={{
                ...typography.caption,
                marginTop: '8px',
                color: getVitalStatus(latestVitals.heart_rate, 'hr') === 'critical'
                  ? colors.critical.text
                  : getVitalStatus(latestVitals.heart_rate, 'hr') === 'warning'
                  ? colors.warning.text
                  : colors.stable.text,
              }}
            >
              ↑ High
            </div>
          </div>

          {/* SpO2 */}
          <div
            style={{
              backgroundColor: colors.neutral.white,
              border: `1px solid ${colors.neutral['300']}`,
              borderRadius: '12px',
              padding: '20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Wind size={20} color={colors.critical.badge} />
              <span style={typography.overline}>SpO2</span>
            </div>
            <div style={{ ...typography.bigNumber, marginBottom: '4px' }}>
              {latestVitals.spo2}%
            </div>
            <div
              style={{
                ...typography.caption,
                marginTop: '8px',
                color: latestVitals.spo2 < 90 ? colors.critical.text : colors.warning.text,
              }}
            >
              ↓ Low
            </div>
          </div>

          {/* Blood Pressure */}
          <div
            style={{
              backgroundColor: colors.neutral.white,
              border: `1px solid ${colors.neutral['300']}`,
              borderRadius: '12px',
              padding: '20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Activity size={20} color={colors.critical.badge} />
              <span style={typography.overline}>Blood Pressure</span>
            </div>
            <div style={{ ...typography.bigNumber, marginBottom: '4px' }}>
              {latestVitals.systolic_bp}/{latestVitals.diastolic_bp}
            </div>
            <div
              style={{
                ...typography.caption,
                marginTop: '8px',
                color: colors.critical.text,
              }}
            >
              ↑ High
            </div>
          </div>

          {/* Risk Score */}
          <div
            style={{
              backgroundColor: colors.neutral.white,
              border: `1px solid ${colors.neutral['300']}`,
              borderRadius: '12px',
              padding: '20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <AlertTriangle size={20} color={colors.critical.badge} />
              <span style={typography.overline}>Risk Level</span>
            </div>
            <div style={{ ...typography.bigNumber, marginBottom: '4px', color: colors.critical.badge }}>
              {riskAssessment?.risk_level?.toUpperCase()}
            </div>
            <div style={{ ...typography.body, color: colors.neutral['700'] }}>
              {(riskAssessment?.risk_score || 0).toFixed(2)}
            </div>
          </div>
        </div>

        {/* Time Range Tabs */}
        <div style={{ marginBottom: '32px', display: 'flex', gap: '8px' }}>
          {['1week', '2weeks', '1month', '3months'].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range as any)}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: timeRange === range ? colors.primary.default : colors.neutral['100'],
                color: timeRange === range ? colors.neutral.white : colors.neutral['700'],
                cursor: 'pointer',
                fontWeight: 500,
                transition: 'all 0.2s',
              }}
            >
              {range === '1week' && '1 Week'}
              {range === '2weeks' && '2 Weeks'}
              {range === '1month' && '1 Month'}
              {range === '3months' && '3 Months'}
            </button>
          ))}
        </div>

        {/* Heart Rate History Chart */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            padding: '24px',
            marginBottom: '32px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}
        >
          <h3 style={{ ...typography.sectionTitle, marginBottom: '16px' }}>Heart Rate History</h3>
          <div
            style={{
              height: '300px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: colors.neutral['50'],
              borderRadius: '8px',
              color: colors.neutral['500'],
            }}
          >
            [Recharts - Heart Rate Zone Chart with overlay bands]
          </div>
        </div>

        {/* Two Column History Panels */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
            gap: '16px',
            marginBottom: '32px',
          }}
        >
          {/* Alert History */}
          <div
            style={{
              backgroundColor: colors.neutral.white,
              border: `1px solid ${colors.neutral['300']}`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <h3 style={{ ...typography.sectionTitle, marginBottom: '16px' }}>Alert History</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ padding: '12px', backgroundColor: colors.critical.background, borderRadius: '8px' }}>
                <div style={{ ...typography.body, color: colors.critical.text, fontWeight: 600 }}>
                  ● Critical: Heart Rate Spike
                </div>
                <div style={{ ...typography.caption, color: colors.critical.text, marginTop: '4px' }}>
                  14 minutes ago
                </div>
              </div>
              <div style={{ padding: '12px', backgroundColor: colors.warning.background, borderRadius: '8px' }}>
                <div style={{ ...typography.body, color: colors.warning.text, fontWeight: 600 }}>
                  ● Warning: Blood Pressure Elevated
                </div>
                <div style={{ ...typography.caption, color: colors.warning.text, marginTop: '4px' }}>
                  34 minutes ago
                </div>
              </div>
            </div>
          </div>

          {/* Session History */}
          <div
            style={{
              backgroundColor: colors.neutral.white,
              border: `1px solid ${colors.neutral['300']}`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <h3 style={{ ...typography.sectionTitle, marginBottom: '16px' }}>Session History</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ padding: '12px', backgroundColor: colors.neutral['50'], borderRadius: '8px' }}>
                <div style={{ ...typography.body, fontWeight: 600 }}>
                  Jan 28: 30-min Walk
                </div>
                <div style={{ ...typography.caption, color: colors.neutral['500'], marginTop: '4px' }}>
                  Avg HR: 84 BPM • Recovery: Good
                </div>
              </div>
              <div style={{ padding: '12px', backgroundColor: colors.neutral['50'], borderRadius: '8px' }}>
                <div style={{ ...typography.body, fontWeight: 600 }}>
                  Jan 27: Rest Day
                </div>
              </div>
              <div style={{ padding: '12px', backgroundColor: colors.neutral['50'], borderRadius: '8px' }}>
                <div style={{ ...typography.body, fontWeight: 600 }}>
                  Jan 26: 20-min Walk
                </div>
                <div style={{ ...typography.caption, color: colors.neutral['500'], marginTop: '4px' }}>
                  Avg HR: 78 BPM • Recovery: Excellent
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* AI Risk Assessment */}
        <div
          style={{
            backgroundColor: colors.critical.background,
            border: `1px solid ${colors.critical.border}`,
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <AlertTriangle size={20} color={colors.critical.text} />
            <h3 style={{ ...typography.sectionTitle, color: colors.critical.text, margin: 0 }}>
              AI Risk Assessment
            </h3>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ ...typography.body, color: colors.critical.text, marginBottom: '8px' }}>
              <strong>Current Risk: {riskAssessment?.risk_level?.toUpperCase()} ({(riskAssessment?.risk_score || 0).toFixed(2)})</strong>
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ ...typography.body, color: colors.critical.text, fontWeight: 600, marginBottom: '8px' }}>
              Contributing Factors:
            </div>
            <ul style={{ margin: 0, paddingLeft: '20px' }}>
              {riskAssessment?.contributing_factors.map((factor, idx) => (
                <li key={idx} style={{ ...typography.body, color: colors.critical.text, marginBottom: '4px' }}>
                  {factor}
                </li>
              ))}
            </ul>
          </div>

          <div style={{ paddingTop: '16px', borderTop: `1px solid ${colors.critical.border}` }}>
            <div style={{ ...typography.body, color: colors.critical.text, fontWeight: 600 }}>
              Recommendation:
            </div>
            <div style={{ ...typography.body, color: colors.critical.text, marginTop: '8px' }}>
              {riskAssessment?.recommendation}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default PatientDetailPage;
