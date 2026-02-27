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
import { ArrowLeft, Heart, Wind, Activity, AlertTriangle, Radar, TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp, Zap, Crosshair, ArrowRight, Check, Loader, Shuffle, Clock, Flame, CheckCircle, XCircle, BarChart2, MessageSquare, FileText, Send, AlertOctagon, Info, Bell, Cpu, HardDrive, RefreshCw, Search, ArrowUpRight, ArrowDownRight } from 'lucide-react';
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
import { api } from '../services/api';
import {
  AlertResponse,
  ActivitySessionResponse,
  RecommendationResponse,
  RiskAssessmentResponse,
  User,
  VitalSignResponse,
  VitalSignsHistoryResponse,
  AnomalyDetectionResponse,
  AnomalyItem,
  TrendForecastResponse,
  BaselineOptimizationResponse,
  RankedRecommendationResponse,
  NaturalLanguageRiskSummaryResponse,
  NaturalLanguageAlertResponse,
  RetrainingStatusResponse,
  RetrainingReadinessResponse,
  ExplainPredictionResponse,
} from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';
import StatusBadge, { riskToStatus } from '../components/common/StatusBadge';

const PatientDetailPage: React.FC = () => {
  const { patientId } = useParams<{ patientId: string }>();
  const navigate = useNavigate();
  const [patient, setPatient] = useState<User | null>(null);
  const [latestVitals, setLatestVitals] = useState<VitalSignResponse | null>(null);
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessmentResponse | null>(null);
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [activities, setActivities] = useState<ActivitySessionResponse[]>([]);
  const [vitalsHistory, setVitalsHistory] = useState<VitalSignsHistoryResponse | null>(null);
  const [anomalyData, setAnomalyData] = useState<AnomalyDetectionResponse | null>(null);
  const [anomalyPage, setAnomalyPage] = useState<number>(1);
  const anomaliesPerPage = 6;
  const [trendData, setTrendData] = useState<TrendForecastResponse | null>(null);
  const [baselineData, setBaselineData] = useState<BaselineOptimizationResponse | null>(null);
  const [baselineApplying, setBaselineApplying] = useState(false);
  const [baselineApplyResult, setBaselineApplyResult] = useState<'success' | 'error' | null>(null);
  const [anomalyHours, setAnomalyHours] = useState<number>(24);
  const [anomalyExpanded, setAnomalyExpanded] = useState(true);
  const [trendExpanded, setTrendExpanded] = useState(true);
  const [baselineExpanded, setBaselineExpanded] = useState(true);
  const [recData, setRecData] = useState<RankedRecommendationResponse | null>(null);
  const [recExpanded, setRecExpanded] = useState(true);
  const [recOutcomeLoading, setRecOutcomeLoading] = useState(false);
  const [recOutcomeResult, setRecOutcomeResult] = useState<'completed' | 'skipped' | 'partial' | null>(null);
  const [riskSummaryData, setRiskSummaryData] = useState<NaturalLanguageRiskSummaryResponse | null>(null);
  const [nlExpanded, setNlExpanded] = useState(true);
  const [nlAlertType, setNlAlertType] = useState('high_heart_rate');
  const [nlSeverity, setNlSeverity] = useState('warning');
  const [nlAlertResult, setNlAlertResult] = useState<NaturalLanguageAlertResponse | null>(null);
  const [nlAlertLoading, setNlAlertLoading] = useState(false);
  const [retrainStatus, setRetrainStatus] = useState<RetrainingStatusResponse | null>(null);
  const [retrainReadiness, setRetrainReadiness] = useState<RetrainingReadinessResponse | null>(null);
  const [modelExpanded, setModelExpanded] = useState(true);
  const [explainData, setExplainData] = useState<ExplainPredictionResponse | null>(null);
  const [explainExpanded, setExplainExpanded] = useState(true);
  const [explainLoading, setExplainLoading] = useState(false);
  const [timeRange, setTimeRange] = useState<'1week' | '2weeks' | '1month' | '3months'>('1week');
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [computingRisk, setComputingRisk] = useState(false);
  const [computeRiskMessage, setComputeRiskMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadPatientData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId, timeRange]);

  const rangeToDays = (range: typeof timeRange) => {
    switch (range) {
      case '2weeks':
        return 14;
      case '1month':
        return 30;
      case '3months':
        return 90;
      case '1week':
      default:
        return 7;
    }
  };

  const loadPatientData = async () => {
    try {
      setLoading(true);
      setErrorMessage(null);

      if (!patientId) {
        throw new Error('Missing patient id');
      }

      const userId = Number(patientId);
      if (Number.isNaN(userId)) {
        throw new Error('Invalid patient id');
      }

      const days = rangeToDays(timeRange);

      const results = await Promise.allSettled([
        api.getUserById(userId),
        api.getLatestVitalSignsForUser(userId),
        api.getLatestRiskAssessmentForUser(userId),
        api.getLatestRecommendationForUser(userId),
        api.getAlertsForUser(userId, 1, 5),
        api.getActivitiesForUser(userId, 5, 0),
        api.getVitalSignsHistoryForUser(userId, days, 1, 100),
        api.getAnomalyDetection(userId, anomalyHours),
        api.getTrendForecast(userId, days),
        api.getBaselineOptimization(userId, days),
        api.getRankedRecommendation(userId, riskAssessment?.risk_level || 'low'),
        api.getNaturalLanguageRiskSummary(userId),
        api.getRetrainingStatus(),
        api.getRetrainingReadiness(),
      ]);

      const [userResult, vitalsResult, riskResult, recResult, alertsResult, activitiesResult, historyResult, anomalyResult, trendResult, baselineResult, recRankResult, riskSummaryResult, retrainStatusResult, retrainReadinessResult] = results;
      const errors: string[] = [];

      if (userResult.status === 'fulfilled') {
        setPatient(userResult.value);
      } else {
        setPatient(null);
        errors.push('patient profile');
      }

      if (vitalsResult.status === 'fulfilled') {
        setLatestVitals(vitalsResult.value);
      } else {
        setLatestVitals(null);
        errors.push('latest vitals');
      }

      if (riskResult.status === 'fulfilled') {
        setRiskAssessment(riskResult.value);
      } else {
        setRiskAssessment(null);
        // 404 is expected for patients who haven't had a risk assessment computed yet
      }

      if (recResult.status === 'fulfilled') {
        setRecommendation(recResult.value);
      } else {
        setRecommendation(null);
        // 404 is expected for patients who haven't had a recommendation generated yet
      }

      if (alertsResult.status === 'fulfilled') {
        setAlerts(alertsResult.value.alerts ?? []);
      } else {
        setAlerts([]);
        errors.push('alerts');
      }

      if (activitiesResult.status === 'fulfilled') {
        setActivities(activitiesResult.value.activities ?? []);
      } else {
        setActivities([]);
        errors.push('activity sessions');
      }

      if (historyResult.status === 'fulfilled') {
        setVitalsHistory(historyResult.value);
      } else {
        setVitalsHistory(null);
        errors.push('vitals history');
      }

      // Advanced ML: Anomaly Detection (optional - don't count as error)
      if (anomalyResult.status === 'fulfilled') {
        setAnomalyData(anomalyResult.value);
      } else {
        setAnomalyData(null);
        // Don't push error - advanced ML features are optional
      }

      // Advanced ML: Trend Forecast (optional - don't count as error)
      if (trendResult.status === 'fulfilled') {
        setTrendData(trendResult.value);
      } else {
        setTrendData(null);
        // Don't push error - advanced ML features are optional
      }

      // Advanced ML: Baseline Optimization (optional - don't count as error)
      if (baselineResult.status === 'fulfilled') {
        setBaselineData(baselineResult.value);
        setBaselineApplyResult(null);
      } else {
        setBaselineData(null);
        // Don't push error - advanced ML features are optional
      }

      // Advanced ML: Recommendation Ranking (optional - don't count as error)
      if (recRankResult.status === 'fulfilled') {
        setRecData(recRankResult.value);
        setRecOutcomeResult(null);
      } else {
        setRecData(null);
        // Don't push error - advanced ML features are optional
      }

      // Advanced ML: Natural Language Risk Summary
      if (riskSummaryResult.status === 'fulfilled') {
        setRiskSummaryData(riskSummaryResult.value);
      } else {
        setRiskSummaryData(null);
        // Don't push error — 404 is expected if no risk assessments exist
      }

      // Advanced ML: Model Retraining Status
      if (retrainStatusResult.status === 'fulfilled') {
        setRetrainStatus(retrainStatusResult.value);
      } else {
        setRetrainStatus(null);
      }

      // Advanced ML: Model Retraining Readiness
      if (retrainReadinessResult.status === 'fulfilled') {
        setRetrainReadiness(retrainReadinessResult.value);
      } else {
        setRetrainReadiness(null);
      }

      if (errors.length > 0) {
        setErrorMessage(`Some data failed to load: ${errors.join(', ')}`);
      }
    } catch (error) {
      console.error('Error loading patient data:', error);
      setErrorMessage(`Failed to load patient data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleComputeRisk = async () => {
    if (!patientId) return;
    const userId = Number(patientId);
    setComputingRisk(true);
    setComputeRiskMessage(null);
    try {
      await api.computeRiskAssessmentForUser(userId);
      setComputeRiskMessage({ type: 'success', text: 'AI assessment complete. Refreshing data...' });
      await loadPatientData();
    } catch (err: any) {
      let detail = err?.response?.data?.detail || 'Unable to compute risk. The patient needs recent vitals submitted within the last 30 minutes.';
      
      // Check if it's a 503 error (model not loaded)
      if (err?.response?.status === 503) {
        detail = 'ML model not loaded on backend. Check backend logs, ensure model files exist in ml_models/, and restart the backend.';
      }
      
      setComputeRiskMessage({ type: 'error', text: detail });
    } finally {
      setComputingRisk(false);
    }
  };

  const formatTimeAgo = (isoDate?: string) => {
    if (!isoDate) return 'Just now';
    const date = new Date(isoDate);
    const diffMs = Date.now() - date.getTime();
    const diffMin = Math.max(1, Math.floor(diffMs / 60000));
    if (diffMin < 60) return `${diffMin} min ago`;
    const diffHr = Math.floor(diffMin / 60);
    return `${diffHr} hr${diffHr > 1 ? 's' : ''} ago`;
  };

  const getRiskFactors = () => {
    const raw = riskAssessment?.risk_factors_json;
    if (!raw) return [] as string[];
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed.map((item) => String(item));
      }
      if (typeof parsed === 'object' && parsed !== null) {
        return Object.values(parsed).map((item) => String(item));
      }
      return [String(parsed)];
    } catch {
      return [raw];
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '32px', textAlign: 'center' }}>
        <p>Loading patient data...</p>
      </div>
    );
  }

  if (!patient) {
    return (
      <div style={{ padding: '32px' }}>
        <p>{errorMessage || 'Patient data not found'}</p>
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
  const riskFactors = getRiskFactors();
  const vitalsAny = latestVitals as VitalSignResponse & {
    blood_pressure_systolic?: number;
    blood_pressure_diastolic?: number;
  } | null;
  const systolic = vitalsAny?.blood_pressure?.systolic ?? vitalsAny?.blood_pressure_systolic ?? 0;
  const diastolic = vitalsAny?.blood_pressure?.diastolic ?? vitalsAny?.blood_pressure_diastolic ?? 0;
  const heartRate = latestVitals?.heart_rate ?? null;
  const spo2Value = latestVitals?.spo2 ?? null;

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
        {errorMessage && (
          <div
            style={{
              backgroundColor: colors.warning.background,
              border: `1px solid ${colors.warning.border}`,
              color: colors.warning.text,
              padding: '12px 16px',
              borderRadius: '8px',
              marginBottom: '16px',
            }}
          >
            {errorMessage}
          </div>
        )}
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
              {patient.full_name?.substring(0, 2).toUpperCase()}
            </div>

            {/* Patient Info */}
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
                <h1 style={{ ...typography.sectionTitle, margin: 0 }}>{patient.full_name}</h1>
                <StatusBadge status={riskStatus} />
              </div>
              <p style={{ ...typography.body, margin: '4px 0' }}>
                {patient.gender?.charAt(0).toUpperCase()}{patient.gender?.slice(1) || 'N/A'}, {patient.age} years old
              </p>
              <p style={{ ...typography.caption, margin: '4px 0' }}>
                Last reading: {formatTimeAgo(latestVitals?.timestamp)}
              </p>
              <p style={{ ...typography.caption, margin: '4px 0' }}>
                Device: {latestVitals?.source_device || 'Unknown device'}
              </p>
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
              {heartRate ?? '--'}
            </div>
            <div style={typography.bigNumberUnit}>{heartRate != null ? 'BPM' : ''}</div>
            <div
              style={{
                ...typography.caption,
                marginTop: '8px',
                color: heartRate == null
                  ? colors.neutral['500']
                  : getVitalStatus(heartRate, 'hr') === 'critical'
                  ? colors.critical.text
                  : getVitalStatus(heartRate, 'hr') === 'warning'
                  ? colors.warning.text
                  : colors.stable.text,
              }}
            >
              {heartRate == null ? 'No data' : '↑ High'}
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
              {spo2Value != null ? `${spo2Value.toFixed(0)}%` : '--'}
            </div>
            <div
              style={{
                ...typography.caption,
                marginTop: '8px',
                color: spo2Value == null
                  ? colors.neutral['500']
                  : spo2Value < 90
                  ? colors.critical.text
                  : colors.warning.text,
              }}
            >
              {spo2Value == null ? 'No data' : '↓ Low'}
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
              {systolic || '--'}/{diastolic || '--'}
            </div>
            <div
              style={{
                ...typography.caption,
                marginTop: '8px',
                color: systolic === 0
                  ? colors.neutral['500']
                  : getVitalStatus(systolic, 'bp') === 'critical'
                  ? colors.critical.text
                  : getVitalStatus(systolic, 'bp') === 'warning'
                  ? colors.warning.text
                  : colors.stable.text,
              }}
            >
              {systolic === 0 ? 'No data' : '↑ High'}
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
            {riskAssessment ? (
              <>
                <div style={{ ...typography.bigNumber, marginBottom: '4px', color: colors.critical.badge }}>
                  {riskAssessment.risk_level?.toUpperCase()}
                </div>
                <div style={{ ...typography.body, color: colors.neutral['700'] }}>
                  {riskAssessment.risk_score.toFixed(2)}
                </div>
              </>
            ) : (
              <button
                onClick={handleComputeRisk}
                disabled={computingRisk}
                style={{
                  marginTop: '4px',
                  padding: '8px 12px',
                  backgroundColor: colors.primary.default,
                  color: colors.neutral.white,
                  border: 'none',
                  borderRadius: '6px',
                  cursor: computingRisk ? 'not-allowed' : 'pointer',
                  fontSize: '12px',
                  fontWeight: 500,
                  opacity: computingRisk ? 0.7 : 1,
                  width: '100%',
                }}
              >
                {computingRisk ? 'Computing...' : 'Run AI Assessment'}
              </button>
            )}
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
                <XAxis
                  dataKey="time"
                  stroke={colors.neutral['500']}
                  style={{ fontSize: '12px' }}
                />
                <YAxis
                  stroke={colors.neutral['500']}
                  style={{ fontSize: '12px' }}
                  domain={[40, 180]}
                />
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
                <Line
                  type="monotone"
                  dataKey="hr"
                  stroke={colors.critical.badge}
                  name="Heart Rate (BPM)"
                  dot={false}
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="spo2"
                  stroke={colors.warning.badge}
                  name="SpO2 (%)"
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
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
              No vitals history available for chart
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* Advanced ML: Anomaly Detection Panel                            */}
        {/* ================================================================= */}
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
          {/* Collapsible header */}
          <button
            onClick={() => setAnomalyExpanded(!anomalyExpanded)}
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
              borderBottom: anomalyExpanded ? `1px solid ${colors.neutral['300']}` : 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Radar size={22} color={anomalyData && anomalyData.anomaly_count > 0 ? colors.warning.text : colors.primary.default} />
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
            {anomalyExpanded ? <ChevronUp size={20} color={colors.neutral['500']} /> : <ChevronDown size={20} color={colors.neutral['500']} />}
          </button>

          {/* Expanded content */}
          {anomalyExpanded && (
            <div style={{ padding: '24px' }}>
              {/* Controls row */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
                <span style={{ ...typography.caption, fontWeight: 600 }}>Window:</span>
                {[6, 12, 24, 48, 72, 168].map((h) => (
                  <button
                    key={h}
                    onClick={async () => {
                      setAnomalyHours(h);
                      setAnomalyPage(1);
                      if (patientId) {
                        try {
                          const res = await api.getAnomalyDetection(Number(patientId), h);
                          setAnomalyData(res);
                        } catch (e) {
                          console.error('Anomaly fetch failed:', e);
                        }
                      }
                    }}
                    style={{
                      padding: '4px 12px',
                      borderRadius: '6px',
                      border: 'none',
                      backgroundColor: anomalyHours === h ? colors.primary.default : colors.neutral['100'],
                      color: anomalyHours === h ? colors.neutral.white : colors.neutral['700'],
                      cursor: 'pointer',
                      fontWeight: 500,
                      fontSize: '13px',
                      transition: 'all 0.15s',
                    }}
                  >
                    {h < 24 ? `${h}h` : `${h / 24}d`}
                  </button>
                ))}
              </div>

              {/* Stats summary row */}
              {anomalyData && anomalyData.stats && (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: '12px',
                    marginBottom: '20px',
                    padding: '16px',
                    backgroundColor: colors.neutral['50'],
                    borderRadius: '8px',
                  }}
                >
                  <div>
                    <div style={{ ...typography.caption, color: colors.neutral['500'] }}>HR Mean</div>
                    <div style={{ ...typography.body, fontWeight: 700 }}>{anomalyData.stats.hr_mean?.toFixed(1) ?? '--'} BPM</div>
                  </div>
                  <div>
                    <div style={{ ...typography.caption, color: colors.neutral['500'] }}>HR Std Dev</div>
                    <div style={{ ...typography.body, fontWeight: 700 }}>±{anomalyData.stats.hr_std?.toFixed(1) ?? '--'}</div>
                  </div>
                  <div>
                    <div style={{ ...typography.caption, color: colors.neutral['500'] }}>SpO2 Mean</div>
                    <div style={{ ...typography.body, fontWeight: 700 }}>{anomalyData.stats.spo2_mean?.toFixed(1) ?? '--'}%</div>
                  </div>
                  <div>
                    <div style={{ ...typography.caption, color: colors.neutral['500'] }}>Readings</div>
                    <div style={{ ...typography.body, fontWeight: 700 }}>{anomalyData.total_readings}</div>
                  </div>
                </div>
              )}

              {/* Anomaly list */}
              {!anomalyData || anomalyData.status === 'insufficient_data' ? (
                <div
                  style={{
                    padding: '24px',
                    textAlign: 'center',
                    backgroundColor: colors.neutral['50'],
                    borderRadius: '8px',
                    color: colors.neutral['500'],
                  }}
                >
                  {anomalyData?.message || 'Not enough data for anomaly detection. Need at least 3 readings.'}
                </div>
              ) : anomalyData.anomaly_count === 0 ? (
                <div
                  style={{
                    padding: '20px',
                    textAlign: 'center',
                    backgroundColor: colors.stable.background,
                    borderRadius: '8px',
                    border: `1px solid ${colors.stable.border}`,
                    color: colors.stable.text,
                    fontWeight: 600,
                  }}
                >
                  No anomalies detected in the last {anomalyHours < 24 ? `${anomalyHours} hours` : `${anomalyHours / 24} day(s)`}. All vitals within normal statistical range.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {/* Sort anomalies by severity (critical first) */}
                  {(() => {
                    const sortedAnomalies = [...anomalyData.anomalies].sort((a, b) => {
                      const aCritical = (a.metric === 'spo2' && a.direction === 'low')
                        || (a.metric === 'heart_rate' && a.direction === 'high')
                        || a.metric === 'hr_variability';
                      const bCritical = (b.metric === 'spo2' && b.direction === 'low')
                        || (b.metric === 'heart_rate' && b.direction === 'high')
                        || b.metric === 'hr_variability';
                      return (bCritical ? 1 : 0) - (aCritical ? 1 : 0);
                    });

                    const totalPages = Math.ceil(sortedAnomalies.length / anomaliesPerPage);
                    const startIdx = (anomalyPage - 1) * anomaliesPerPage;
                    const paginatedAnomalies = sortedAnomalies.slice(startIdx, startIdx + anomaliesPerPage);

                    return (
                      <>
                        {paginatedAnomalies.map((a: AnomalyItem, idx: number) => {
                          // Determine severity color by metric and direction
                          const isCritical = (a.metric === 'spo2' && a.direction === 'low')
                            || (a.metric === 'heart_rate' && a.direction === 'high')
                            || a.metric === 'hr_variability';
                          const bg = isCritical ? colors.critical.background : colors.warning.background;
                          const border = isCritical ? colors.critical.border : colors.warning.border;
                          const text = isCritical ? colors.critical.text : colors.warning.text;
                          const badge = isCritical ? colors.critical.badge : colors.warning.badge;

                          // Icon for metric type
                          const MetricIcon = a.metric === 'heart_rate' ? Heart
                            : a.metric === 'spo2' ? Wind
                            : Zap;

                          // Human-readable metric label
                          const metricLabel = a.metric === 'heart_rate' ? 'Heart Rate'
                            : a.metric === 'spo2' ? 'SpO2'
                            : 'HR Variability';

                          // Direction arrow
                          const directionLabel = a.direction === 'high' ? '↑ Unusually High'
                            : a.direction === 'low' ? '↓ Unusually Low'
                            : a.direction === 'spike' ? '↑ Sudden Spike'
                            : '↓ Sudden Drop';

                          return (
                            <div
                              key={idx}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '16px',
                                padding: '14px 18px',
                                backgroundColor: bg,
                                border: `1px solid ${border}`,
                                borderRadius: '8px',
                              }}
                            >
                              {/* Icon circle */}
                              <div
                                style={{
                                  width: '36px',
                                  height: '36px',
                                  borderRadius: '50%',
                                  backgroundColor: badge,
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  flexShrink: 0,
                                }}
                              >
                                <MetricIcon size={18} color="#fff" />
                              </div>

                              {/* Details */}
                              <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <span style={{ ...typography.body, fontWeight: 700, color: text }}>
                                    {metricLabel}: {a.value}{a.metric === 'spo2' ? '%' : a.metric === 'heart_rate' ? ' BPM' : ' BPM Δ'}
                                  </span>
                                  <span
                                    style={{
                                      fontSize: '11px',
                                      fontWeight: 600,
                                      color: badge,
                                      backgroundColor: `${badge}20`,
                                      padding: '2px 8px',
                                      borderRadius: '4px',
                                    }}
                                  >
                                    {directionLabel}
                                  </span>
                                </div>
                                <div style={{ ...typography.caption, color: text, marginTop: '4px' }}>
                                  {a.z_score != null ? `Z-score: ${a.z_score.toFixed(2)} (threshold: ${anomalyData.z_threshold})` : 'Consecutive reading jump'}
                                  {a.timestamp && ` • ${new Date(a.timestamp).toLocaleString()}`}
                                </div>
                              </div>
                            </div>
                          );
                        })}

                        {/* Pagination controls */}
                        {totalPages > 1 && (
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', marginTop: '16px', paddingTop: '12px', borderTop: `1px solid ${colors.neutral['200']}` }}>
                            <button
                              onClick={() => setAnomalyPage(Math.max(1, anomalyPage - 1))}
                              disabled={anomalyPage === 1}
                              style={{
                                padding: '6px 12px',
                                borderRadius: '6px',
                                border: `1px solid ${colors.neutral['300']}`,
                                backgroundColor: anomalyPage === 1 ? colors.neutral['100'] : colors.neutral.white,
                                color: anomalyPage === 1 ? colors.neutral['400'] : colors.neutral['700'],
                                cursor: anomalyPage === 1 ? 'not-allowed' : 'pointer',
                                fontSize: '13px',
                                fontWeight: 600,
                              }}
                            >
                              ← Previous
                            </button>
                            <span style={{ ...typography.caption, color: colors.neutral['600'], fontWeight: 600 }}>
                              Page {anomalyPage} of {totalPages}
                            </span>
                            <button
                              onClick={() => setAnomalyPage(Math.min(totalPages, anomalyPage + 1))}
                              disabled={anomalyPage === totalPages}
                              style={{
                                padding: '6px 12px',
                                borderRadius: '6px',
                                border: `1px solid ${colors.neutral['300']}`,
                                backgroundColor: anomalyPage === totalPages ? colors.neutral['100'] : colors.neutral.white,
                                color: anomalyPage === totalPages ? colors.neutral['400'] : colors.neutral['700'],
                                cursor: anomalyPage === totalPages ? 'not-allowed' : 'pointer',
                                fontSize: '13px',
                                fontWeight: 600,
                              }}
                            >
                              Next →
                            </button>
                          </div>
                        )}
                      </>
                    );
                  })()}
                </div>
              )}

              {/* ML Model not available message */}
              {!anomalyData && (
                <div
                  style={{
                    padding: '18px 22px',
                    backgroundColor: colors.neutral['50'],
                    border: `1px solid ${colors.neutral['200']}`,
                    borderRadius: '8px',
                    marginTop: '16px',
                  }}
                >
                  <div style={{ ...typography.body, color: colors.neutral['600'], marginBottom: '8px', fontWeight: 600 }}>
                    ⚠️ Advanced ML features unavailable
                  </div>
                  <div style={{ ...typography.body, color: colors.neutral['600'], marginBottom: '8px' }}>
                    The backend ML model is not loaded. To enable anomaly detection and other advanced features:
                  </div>
                  <ul style={{ ...typography.body, color: colors.neutral['600'], margin: '8px 0', paddingLeft: '24px', lineHeight: '1.6' }}>
                    <li>Check backend logs for model loading errors</li>
                    <li>Ensure <code style={{fontFamily: 'monospace', backgroundColor: colors.neutral['100'], padding: '2px 6px', borderRadius: '3px'}}>ml_models/</code> folder contains: risk_model.pkl, scaler.pkl, feature_columns.json</li>
                    <li>Restart backend: <code style={{fontFamily: 'monospace', backgroundColor: colors.neutral['100'], padding: '2px 6px', borderRadius: '3px'}}>python start_server.py</code></li>
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* Advanced ML: Trend Forecast Panel                                */}
        {/* ================================================================= */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            marginBottom: '32px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            overflow: 'hidden',
          }}
        >
          {/* Collapsible header */}
          <button
            onClick={() => setTrendExpanded(!trendExpanded)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '20px 24px',
              backgroundColor: trendData?.risk_projection?.risk_direction === 'increasing'
                ? colors.critical.background
                : trendData?.risk_projection?.risk_direction === 'decreasing'
                ? colors.stable.background
                : colors.neutral.white,
              border: 'none',
              cursor: 'pointer',
              borderBottom: trendExpanded ? `1px solid ${colors.neutral['300']}` : 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <TrendingUp size={22} color={colors.primary.default} />
              <span style={{ ...typography.sectionTitle, margin: 0 }}>Trend Forecast</span>
              {trendData?.risk_projection && (
                <span
                  style={{
                    backgroundColor: trendData.risk_projection.risk_direction === 'increasing'
                      ? colors.critical.badge
                      : trendData.risk_projection.risk_direction === 'decreasing'
                      ? colors.stable.badge
                      : colors.neutral['500'],
                    color: colors.neutral.white,
                    fontSize: '12px',
                    fontWeight: 700,
                    padding: '2px 10px',
                    borderRadius: '12px',
                  }}
                >
                  Risk {trendData.risk_projection.risk_direction}
                </span>
              )}
            </div>
            {trendExpanded ? <ChevronUp size={20} color={colors.neutral['500']} /> : <ChevronDown size={20} color={colors.neutral['500']} />}
          </button>

          {/* Expanded content */}
          {trendExpanded && (
            <div style={{ padding: '24px' }}>
              {!trendData || trendData.status === 'insufficient_data' ? (
                <div
                  style={{
                    padding: '24px',
                    textAlign: 'center',
                    backgroundColor: colors.neutral['50'],
                    borderRadius: '8px',
                    color: colors.neutral['500'],
                  }}
                >
                  {trendData?.message || 'Not enough historical data for trend forecasting. Need at least 7 readings.'}
                </div>
              ) : (
                <>
                  {/* Trend metric cards */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                      gap: '16px',
                      marginBottom: '24px',
                    }}
                  >
                    {/* Heart Rate Trend */}
                    {trendData.trends.heart_rate && (() => {
                      const t = trendData.trends.heart_rate!;
                      const DirectionIcon = t.direction === 'increasing' ? TrendingUp
                        : t.direction === 'decreasing' ? TrendingDown
                        : Minus;
                      const dirColor = t.direction === 'increasing' ? colors.critical.badge
                        : t.direction === 'decreasing' ? colors.stable.badge
                        : colors.neutral['500'];
                      const dirBg = t.direction === 'increasing' ? colors.critical.background
                        : t.direction === 'decreasing' ? colors.stable.background
                        : colors.neutral['50'];

                      return (
                        <div
                          style={{
                            padding: '20px',
                            backgroundColor: dirBg,
                            borderRadius: '10px',
                            border: `1px solid ${t.direction === 'increasing' ? colors.critical.border : t.direction === 'decreasing' ? colors.stable.border : colors.neutral['300']}`,
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                            <Heart size={18} color={colors.critical.badge} />
                            <span style={{ ...typography.body, fontWeight: 700 }}>Heart Rate Trend</span>
                            <DirectionIcon size={20} color={dirColor} />
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                            <div>
                              <div style={{ ...typography.caption, color: colors.neutral['500'] }}>Current (Fitted)</div>
                              <div style={{ fontSize: '22px', fontWeight: 700 }}>{t.current_fitted} <span style={{ fontSize: '13px', fontWeight: 400 }}>BPM</span></div>
                            </div>
                            <div>
                              <div style={{ ...typography.caption, color: colors.neutral['500'] }}>Forecast ({t.forecast_day}d)</div>
                              <div style={{ fontSize: '22px', fontWeight: 700, color: dirColor }}>{t.forecasted_value} <span style={{ fontSize: '13px', fontWeight: 400 }}>BPM</span></div>
                            </div>
                            <div>
                              <div style={{ ...typography.caption, color: colors.neutral['500'] }}>Rate of Change</div>
                              <div style={{ ...typography.body, fontWeight: 600 }}>{t.slope_per_day > 0 ? '+' : ''}{t.slope_per_day.toFixed(2)} BPM/day</div>
                            </div>
                            <div>
                              <div style={{ ...typography.caption, color: colors.neutral['500'] }}>Confidence (R²)</div>
                              <div style={{ ...typography.body, fontWeight: 600 }}>{(t.r_squared * 100).toFixed(1)}%</div>
                            </div>
                          </div>

                          {/* Mini progress bar showing direction */}
                          <div style={{ marginTop: '14px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Direction</span>
                              <span style={{ ...typography.caption, fontWeight: 700, color: dirColor, textTransform: 'capitalize' }}>{t.direction}</span>
                            </div>
                            <div style={{ height: '6px', backgroundColor: colors.neutral['100'], borderRadius: '3px', overflow: 'hidden' }}>
                              <div
                                style={{
                                  height: '100%',
                                  width: `${Math.min(Math.abs(t.slope_per_day) * 20, 100)}%`,
                                  backgroundColor: dirColor,
                                  borderRadius: '3px',
                                  transition: 'width 0.5s ease',
                                }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })()}

                    {/* SpO2 Trend */}
                    {trendData.trends.spo2 && (() => {
                      const t = trendData.trends.spo2!;
                      // For SpO2, decreasing is BAD (opposite of HR)
                      const DirectionIcon = t.direction === 'increasing' ? TrendingUp
                        : t.direction === 'decreasing' ? TrendingDown
                        : Minus;
                      const dirColor = t.direction === 'decreasing' ? colors.critical.badge
                        : t.direction === 'increasing' ? colors.stable.badge
                        : colors.neutral['500'];
                      const dirBg = t.direction === 'decreasing' ? colors.critical.background
                        : t.direction === 'increasing' ? colors.stable.background
                        : colors.neutral['50'];

                      return (
                        <div
                          style={{
                            padding: '20px',
                            backgroundColor: dirBg,
                            borderRadius: '10px',
                            border: `1px solid ${t.direction === 'decreasing' ? colors.critical.border : t.direction === 'increasing' ? colors.stable.border : colors.neutral['300']}`,
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                            <Wind size={18} color={colors.warning.badge} />
                            <span style={{ ...typography.body, fontWeight: 700 }}>SpO2 Trend</span>
                            <DirectionIcon size={20} color={dirColor} />
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                            <div>
                              <div style={{ ...typography.caption, color: colors.neutral['500'] }}>Current (Fitted)</div>
                              <div style={{ fontSize: '22px', fontWeight: 700 }}>{t.current_fitted}<span style={{ fontSize: '13px', fontWeight: 400 }}>%</span></div>
                            </div>
                            <div>
                              <div style={{ ...typography.caption, color: colors.neutral['500'] }}>Forecast ({t.forecast_day}d)</div>
                              <div style={{ fontSize: '22px', fontWeight: 700, color: dirColor }}>{t.forecasted_value}<span style={{ fontSize: '13px', fontWeight: 400 }}>%</span></div>
                            </div>
                            <div>
                              <div style={{ ...typography.caption, color: colors.neutral['500'] }}>Rate of Change</div>
                              <div style={{ ...typography.body, fontWeight: 600 }}>{t.slope_per_day > 0 ? '+' : ''}{t.slope_per_day.toFixed(2)}%/day</div>
                            </div>
                            <div>
                              <div style={{ ...typography.caption, color: colors.neutral['500'] }}>Confidence (R²)</div>
                              <div style={{ ...typography.body, fontWeight: 600 }}>{(t.r_squared * 100).toFixed(1)}%</div>
                            </div>
                          </div>

                          <div style={{ marginTop: '14px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Direction</span>
                              <span style={{ ...typography.caption, fontWeight: 700, color: dirColor, textTransform: 'capitalize' }}>{t.direction}</span>
                            </div>
                            <div style={{ height: '6px', backgroundColor: colors.neutral['100'], borderRadius: '3px', overflow: 'hidden' }}>
                              <div
                                style={{
                                  height: '100%',
                                  width: `${Math.min(Math.abs(t.slope_per_day) * 40, 100)}%`,
                                  backgroundColor: dirColor,
                                  borderRadius: '3px',
                                  transition: 'width 0.5s ease',
                                }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>

                  {/* Risk Projection Summary */}
                  {trendData.risk_projection && (
                    <div
                      style={{
                        padding: '18px 20px',
                        backgroundColor: trendData.risk_projection.risk_direction === 'increasing'
                          ? colors.critical.background
                          : trendData.risk_projection.risk_direction === 'decreasing'
                          ? colors.stable.background
                          : colors.neutral['50'],
                        borderRadius: '8px',
                        border: `1px solid ${
                          trendData.risk_projection.risk_direction === 'increasing'
                            ? colors.critical.border
                            : trendData.risk_projection.risk_direction === 'decreasing'
                            ? colors.stable.border
                            : colors.neutral['300']
                        }`,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                        <AlertTriangle
                          size={18}
                          color={
                            trendData.risk_projection.risk_direction === 'increasing'
                              ? colors.critical.text
                              : trendData.risk_projection.risk_direction === 'decreasing'
                              ? colors.stable.text
                              : colors.neutral['700']
                          }
                        />
                        <span
                          style={{
                            ...typography.body,
                            fontWeight: 700,
                            color: trendData.risk_projection.risk_direction === 'increasing'
                              ? colors.critical.text
                              : trendData.risk_projection.risk_direction === 'decreasing'
                              ? colors.stable.text
                              : colors.neutral['700'],
                          }}
                        >
                          Risk Projection: {trendData.risk_projection.risk_direction.charAt(0).toUpperCase() + trendData.risk_projection.risk_direction.slice(1)}
                          {trendData.risk_projection.risk_score_delta !== 0 &&
                            ` (Δ ${trendData.risk_projection.risk_score_delta > 0 ? '+' : ''}${trendData.risk_projection.risk_score_delta.toFixed(3)})`}
                        </span>
                      </div>
                      <div
                        style={{
                          ...typography.caption,
                          color: trendData.risk_projection.risk_direction === 'increasing'
                            ? colors.critical.text
                            : trendData.risk_projection.risk_direction === 'decreasing'
                            ? colors.stable.text
                            : colors.neutral['500'],
                        }}
                      >
                        {trendData.risk_projection.factors.join(' • ')}
                      </div>
                      <div style={{ ...typography.caption, color: colors.neutral['500'], marginTop: '8px' }}>
                        Based on {trendData.total_readings} readings over {trendData.analysis_days} days • Forecast: {trendData.forecast_days} days ahead
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* ML Model not available message */}
              {!trendData && (
                <div
                  style={{
                    padding: '18px 22px',
                    backgroundColor: colors.neutral['50'],
                    border: `1px solid ${colors.neutral['200']}`,
                    borderRadius: '8px',
                    marginTop: '16px',
                  }}
                >
                  <div style={{ ...typography.body, color: colors.neutral['600'] }}>
                    💡 Trend forecasting requires ML model to be loaded on backend. See anomaly detection panel above for setup instructions.
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* Advanced ML: Baseline Optimization Panel                         */}
        {/* ================================================================= */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            marginBottom: '32px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            overflow: 'hidden',
          }}
        >
          {/* Collapsible header */}
          <button
            onClick={() => setBaselineExpanded(!baselineExpanded)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '20px 24px',
              backgroundColor: baselineData?.adjusted
                ? colors.primary.ultralight
                : colors.neutral.white,
              border: 'none',
              cursor: 'pointer',
              borderBottom: baselineExpanded ? `1px solid ${colors.neutral['300']}` : 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Crosshair size={22} color={colors.primary.default} />
              <span style={{ ...typography.sectionTitle, margin: 0 }}>Baseline Optimization</span>
              {baselineData?.adjusted && (
                <span
                  style={{
                    backgroundColor: colors.primary.default,
                    color: colors.neutral.white,
                    fontSize: '12px',
                    fontWeight: 700,
                    padding: '2px 10px',
                    borderRadius: '12px',
                  }}
                >
                  Update available
                </span>
              )}
              {baselineData && !baselineData.adjusted && baselineData.status === 'ok' && (
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
                  Optimal
                </span>
              )}
            </div>
            {baselineExpanded ? <ChevronUp size={20} color={colors.neutral['500']} /> : <ChevronDown size={20} color={colors.neutral['500']} />}
          </button>

          {/* Expanded content */}
          {baselineExpanded && (
            <div style={{ padding: '24px' }}>
              {!baselineData || baselineData.status !== 'ok' ? (
                <div
                  style={{
                    padding: '24px',
                    textAlign: 'center',
                    backgroundColor: colors.neutral['50'],
                    borderRadius: '8px',
                    color: colors.neutral['500'],
                  }}
                >
                  {baselineData?.message || 'Not enough resting readings to compute optimized baseline. Need at least 5 resting readings (HR < 100 BPM).'}
                </div>
              ) : (
                <>
                  {/* Current → New baseline visual */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '24px',
                      marginBottom: '28px',
                      padding: '24px',
                      backgroundColor: baselineData.adjusted ? colors.primary.ultralight : colors.neutral['50'],
                      borderRadius: '12px',
                      border: `1px solid ${baselineData.adjusted ? colors.primary.light : colors.neutral['300']}`,
                    }}
                  >
                    {/* Current baseline */}
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ ...typography.caption, color: colors.neutral['500'], marginBottom: '6px' }}>Current Baseline</div>
                      <div style={{ fontSize: '36px', fontWeight: 800, color: colors.neutral['700'] }}>
                        {baselineData.current_baseline ?? '--'}
                      </div>
                      <div style={{ ...typography.caption, color: colors.neutral['500'] }}>BPM</div>
                    </div>

                    {/* Arrow */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                      <ArrowRight
                        size={28}
                        color={baselineData.adjusted ? colors.primary.default : colors.neutral['300']}
                      />
                      {baselineData.adjusted && (
                        <span
                          style={{
                            fontSize: '13px',
                            fontWeight: 700,
                            color: (baselineData.adjustment ?? 0) > 0 ? colors.critical.badge : colors.stable.badge,
                          }}
                        >
                          {(baselineData.adjustment ?? 0) > 0 ? '+' : ''}{baselineData.adjustment} BPM
                        </span>
                      )}
                    </div>

                    {/* New baseline */}
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ ...typography.caption, color: colors.neutral['500'], marginBottom: '6px' }}>Recommended</div>
                      <div
                        style={{
                          fontSize: '36px',
                          fontWeight: 800,
                          color: baselineData.adjusted ? colors.primary.default : colors.stable.badge,
                        }}
                      >
                        {baselineData.new_baseline ?? '--'}
                      </div>
                      <div style={{ ...typography.caption, color: colors.neutral['500'] }}>BPM</div>
                    </div>
                  </div>

                  {/* Confidence meter + stats */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                      gap: '16px',
                      marginBottom: '24px',
                    }}
                  >
                    {/* Confidence */}
                    <div
                      style={{
                        padding: '16px',
                        backgroundColor: colors.neutral['50'],
                        borderRadius: '8px',
                      }}
                    >
                      <div style={{ ...typography.caption, color: colors.neutral['500'], marginBottom: '8px' }}>Confidence</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ flex: 1 }}>
                          <div
                            style={{
                              height: '8px',
                              backgroundColor: colors.neutral['100'],
                              borderRadius: '4px',
                              overflow: 'hidden',
                            }}
                          >
                            <div
                              style={{
                                height: '100%',
                                width: `${(baselineData.confidence ?? 0) * 100}%`,
                                backgroundColor:
                                  (baselineData.confidence ?? 0) >= 0.7
                                    ? colors.stable.badge
                                    : (baselineData.confidence ?? 0) >= 0.4
                                    ? colors.warning.badge
                                    : colors.critical.badge,
                                borderRadius: '4px',
                                transition: 'width 0.5s ease',
                              }}
                            />
                          </div>
                        </div>
                        <span style={{ ...typography.body, fontWeight: 700, minWidth: '42px', textAlign: 'right' }}>
                          {((baselineData.confidence ?? 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    {/* Resting HR stats */}
                    <div
                      style={{
                        padding: '16px',
                        backgroundColor: colors.neutral['50'],
                        borderRadius: '8px',
                      }}
                    >
                      <div style={{ ...typography.caption, color: colors.neutral['500'], marginBottom: '8px' }}>Resting HR Stats</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                        <div>
                          <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Mean: </span>
                          <span style={{ ...typography.body, fontWeight: 600 }}>{baselineData.stats?.mean_hr ?? '--'}</span>
                        </div>
                        <div>
                          <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Std: </span>
                          <span style={{ ...typography.body, fontWeight: 600 }}>±{baselineData.stats?.std_hr ?? '--'}</span>
                        </div>
                        <div>
                          <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Min: </span>
                          <span style={{ ...typography.body, fontWeight: 600 }}>{baselineData.stats?.min_hr ?? '--'}</span>
                        </div>
                        <div>
                          <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Max: </span>
                          <span style={{ ...typography.body, fontWeight: 600 }}>{baselineData.stats?.max_hr ?? '--'}</span>
                        </div>
                      </div>
                    </div>

                    {/* Readings used */}
                    <div
                      style={{
                        padding: '16px',
                        backgroundColor: colors.neutral['50'],
                        borderRadius: '8px',
                      }}
                    >
                      <div style={{ ...typography.caption, color: colors.neutral['500'], marginBottom: '8px' }}>Data Quality</div>
                      <div style={{ ...typography.body, fontWeight: 700, marginBottom: '4px' }}>
                        {baselineData.readings_used} / {baselineData.readings_total} readings
                      </div>
                      <div style={{ ...typography.caption, color: colors.neutral['500'] }}>
                        From last {baselineData.data_window_days} days • Outliers filtered
                      </div>
                    </div>
                  </div>

                  {/* Apply button */}
                  {baselineData.adjusted && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                      <button
                        onClick={async () => {
                          if (!patientId) return;
                          setBaselineApplying(true);
                          setBaselineApplyResult(null);
                          try {
                            const res = await api.applyBaselineOptimization(Number(patientId));
                            if (res.applied) {
                              setBaselineApplyResult('success');
                              // Refresh the baseline data to reflect the new current baseline
                              const fresh = await api.getBaselineOptimization(Number(patientId));
                              setBaselineData(fresh);
                              // Also refresh patient profile to update header baseline
                              const updatedPatient = await api.getUserById(Number(patientId));
                              setPatient(updatedPatient);
                            } else {
                              setBaselineApplyResult('error');
                            }
                          } catch (e) {
                            console.error('Baseline apply failed:', e);
                            setBaselineApplyResult('error');
                          } finally {
                            setBaselineApplying(false);
                          }
                        }}
                        disabled={baselineApplying}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '10px 24px',
                          backgroundColor: baselineApplying ? colors.neutral['300'] : colors.primary.default,
                          color: colors.neutral.white,
                          border: 'none',
                          borderRadius: '8px',
                          cursor: baselineApplying ? 'not-allowed' : 'pointer',
                          fontWeight: 600,
                          fontSize: '14px',
                          transition: 'all 0.15s',
                        }}
                      >
                        {baselineApplying ? (
                          <><Loader size={16} className="spin" /> Applying...</>
                        ) : (
                          <><Crosshair size={16} /> Apply Optimized Baseline</>
                        )}
                      </button>

                      {/* Result feedback */}
                      {baselineApplyResult === 'success' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: colors.stable.text }}>
                          <Check size={18} />
                          <span style={{ fontWeight: 600, fontSize: '14px' }}>Baseline updated successfully</span>
                        </div>
                      )}
                      {baselineApplyResult === 'error' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: colors.critical.text }}>
                          <AlertTriangle size={18} />
                          <span style={{ fontWeight: 600, fontSize: '14px' }}>Failed to apply baseline</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Already optimal message */}
                  {!baselineData.adjusted && (
                    <div
                      style={{
                        padding: '16px 20px',
                        backgroundColor: colors.stable.background,
                        border: `1px solid ${colors.stable.border}`,
                        borderRadius: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        color: colors.stable.text,
                      }}
                    >
                      <Check size={18} />
                      <span style={{ fontWeight: 600 }}>
                        Current baseline is optimal. No adjustment needed based on recent resting data.
                      </span>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* Advanced ML: Recommendation Ranking Panel (A/B Testing)         */}
        {/* ================================================================= */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            marginBottom: '32px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            overflow: 'hidden',
          }}
        >
          {/* Collapsible header */}
          <button
            onClick={() => setRecExpanded(!recExpanded)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '20px 24px',
              backgroundColor: colors.neutral.white,
              border: 'none',
              cursor: 'pointer',
              borderBottom: recExpanded ? `1px solid ${colors.neutral['300']}` : 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Shuffle size={22} color={colors.primary.default} />
              <span style={{ ...typography.sectionTitle, margin: 0 }}>Activity Recommendation</span>
              {recData && (
                <span
                  style={{
                    backgroundColor: colors.neutral['100'],
                    color: colors.neutral['600'],
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '2px 10px',
                    borderRadius: '12px',
                    letterSpacing: '0.5px',
                  }}
                >
                  A/B Variant {recData.variant}
                </span>
              )}
              {recData && (
                <span
                  style={{
                    backgroundColor:
                      recData.risk_level === 'high' ? colors.critical.background
                      : recData.risk_level === 'moderate' ? colors.warning.background
                      : colors.stable.background,
                    color:
                      recData.risk_level === 'high' ? colors.critical.text
                      : recData.risk_level === 'moderate' ? colors.warning.text
                      : colors.stable.text,
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '2px 10px',
                    borderRadius: '12px',
                    textTransform: 'capitalize' as const,
                  }}
                >
                  {recData.risk_level} risk
                </span>
              )}
            </div>
            {recExpanded ? <ChevronUp size={20} color={colors.neutral['500']} /> : <ChevronDown size={20} color={colors.neutral['500']} />}
          </button>

          {/* Expanded content */}
          {recExpanded && (
            <div style={{ padding: '24px' }}>
              {!recData ? (
                <div
                  style={{
                    padding: '24px',
                    textAlign: 'center',
                    backgroundColor: colors.neutral['50'],
                    borderRadius: '8px',
                    color: colors.neutral['500'],
                  }}
                >
                  No recommendation data available for this patient.
                </div>
              ) : (
                <>
                  {/* Recommendation card */}
                  <div
                    style={{
                      padding: '24px',
                      backgroundColor:
                        recData.risk_level === 'high' ? colors.critical.background
                        : recData.risk_level === 'moderate' ? colors.warning.background
                        : colors.stable.background,
                      border: `1px solid ${
                        recData.risk_level === 'high' ? colors.critical.border
                        : recData.risk_level === 'moderate' ? colors.warning.border
                        : colors.stable.border
                      }`,
                      borderRadius: '12px',
                      marginBottom: '20px',
                    }}
                  >
                    {/* Title row */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                      <div
                        style={{
                          width: '44px',
                          height: '44px',
                          borderRadius: '50%',
                          backgroundColor:
                            recData.risk_level === 'high' ? colors.critical.badge
                            : recData.risk_level === 'moderate' ? colors.warning.badge
                            : colors.stable.badge,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <Activity size={22} color={colors.neutral.white} />
                      </div>
                      <div>
                        <div style={{ fontSize: '18px', fontWeight: 700, color: colors.neutral['900'] }}>
                          {recData.recommendation.title}
                        </div>
                        <div style={{ ...typography.caption, color: colors.neutral['500'] }}>
                          Experiment: {recData.experiment_id}
                        </div>
                      </div>
                    </div>

                    {/* Description */}
                    <p style={{ ...typography.body, color: colors.neutral['700'], marginBottom: '20px', lineHeight: '1.6' }}>
                      {recData.recommendation.description}
                    </p>

                    {/* Details grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                      <div
                        style={{
                          padding: '12px',
                          backgroundColor: 'rgba(255,255,255,0.7)',
                          borderRadius: '8px',
                          textAlign: 'center',
                        }}
                      >
                        <Flame size={18} color={colors.neutral['500']} style={{ marginBottom: '4px' }} />
                        <div style={{ ...typography.caption, color: colors.neutral['500'], marginBottom: '2px' }}>Activity</div>
                        <div style={{ ...typography.body, fontWeight: 700, fontSize: '13px' }}>
                          {recData.recommendation.suggested_activity}
                        </div>
                      </div>
                      <div
                        style={{
                          padding: '12px',
                          backgroundColor: 'rgba(255,255,255,0.7)',
                          borderRadius: '8px',
                          textAlign: 'center',
                        }}
                      >
                        <BarChart2 size={18} color={colors.neutral['500']} style={{ marginBottom: '4px' }} />
                        <div style={{ ...typography.caption, color: colors.neutral['500'], marginBottom: '2px' }}>Intensity</div>
                        <div style={{
                          ...typography.body,
                          fontWeight: 700,
                          fontSize: '13px',
                          textTransform: 'capitalize' as const,
                        }}>
                          {recData.recommendation.intensity_level}
                        </div>
                      </div>
                      <div
                        style={{
                          padding: '12px',
                          backgroundColor: 'rgba(255,255,255,0.7)',
                          borderRadius: '8px',
                          textAlign: 'center',
                        }}
                      >
                        <Clock size={18} color={colors.neutral['500']} style={{ marginBottom: '4px' }} />
                        <div style={{ ...typography.caption, color: colors.neutral['500'], marginBottom: '2px' }}>Duration</div>
                        <div style={{ ...typography.body, fontWeight: 700, fontSize: '13px' }}>
                          {recData.recommendation.duration_minutes} min
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Outcome recording section - doctor records whether patient followed through */}
                  <div
                    style={{
                      padding: '20px',
                      backgroundColor: colors.neutral['50'],
                      borderRadius: '10px',
                      border: `1px solid ${colors.neutral['200']}`,
                    }}
                  >
                    <div style={{ ...typography.caption, color: colors.neutral['500'], marginBottom: '12px', fontWeight: 600 }}>
                      Record Patient Outcome (A/B Tracking)
                    </div>

                    {recOutcomeResult ? (
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          padding: '12px 16px',
                          backgroundColor:
                            recOutcomeResult === 'completed' ? colors.stable.background
                            : recOutcomeResult === 'skipped' ? colors.critical.background
                            : colors.warning.background,
                          border: `1px solid ${
                            recOutcomeResult === 'completed' ? colors.stable.border
                            : recOutcomeResult === 'skipped' ? colors.critical.border
                            : colors.warning.border
                          }`,
                          borderRadius: '8px',
                        }}
                      >
                        {recOutcomeResult === 'completed' && <CheckCircle size={18} color={colors.stable.text} />}
                        {recOutcomeResult === 'skipped' && <XCircle size={18} color={colors.critical.text} />}
                        {recOutcomeResult === 'partial' && <Clock size={18} color={colors.warning.text} />}
                        <span style={{
                          fontWeight: 600,
                          fontSize: '14px',
                          color:
                            recOutcomeResult === 'completed' ? colors.stable.text
                            : recOutcomeResult === 'skipped' ? colors.critical.text
                            : colors.warning.text,
                          textTransform: 'capitalize' as const,
                        }}>
                          Outcome recorded: {recOutcomeResult}
                        </span>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' as const }}>
                        {(['completed', 'partial', 'skipped'] as const).map((outcome) => (
                          <button
                            key={outcome}
                            disabled={recOutcomeLoading}
                            onClick={async () => {
                              if (!recData || !patientId) return;
                              setRecOutcomeLoading(true);
                              try {
                                await api.recordRecommendationOutcome(
                                  Number(patientId),
                                  recData.experiment_id,
                                  recData.variant,
                                  outcome
                                );
                                setRecOutcomeResult(outcome);
                              } catch (e) {
                                console.error('Failed to record outcome:', e);
                              } finally {
                                setRecOutcomeLoading(false);
                              }
                            }}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '8px 18px',
                              backgroundColor:
                                outcome === 'completed' ? colors.stable.badge
                                : outcome === 'skipped' ? colors.critical.badge
                                : colors.warning.badge,
                              color: colors.neutral.white,
                              border: 'none',
                              borderRadius: '8px',
                              cursor: recOutcomeLoading ? 'not-allowed' : 'pointer',
                              fontWeight: 600,
                              fontSize: '13px',
                              opacity: recOutcomeLoading ? 0.6 : 1,
                              transition: 'opacity 0.15s',
                              textTransform: 'capitalize' as const,
                            }}
                          >
                            {outcome === 'completed' && <CheckCircle size={15} />}
                            {outcome === 'skipped' && <XCircle size={15} />}
                            {outcome === 'partial' && <Clock size={15} />}
                            {recOutcomeLoading ? 'Recording...' : outcome}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* Advanced ML: Natural Language Insights Panel                     */}
        {/* ================================================================= */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            marginBottom: '32px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            overflow: 'hidden',
          }}
        >
          {/* Collapsible header */}
          <button
            onClick={() => setNlExpanded(!nlExpanded)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '20px 24px',
              backgroundColor: colors.neutral.white,
              border: 'none',
              cursor: 'pointer',
              borderBottom: nlExpanded ? `1px solid ${colors.neutral['300']}` : 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <MessageSquare size={22} color={colors.primary.default} />
              <span style={{ ...typography.sectionTitle, margin: 0 }}>Natural Language Insights</span>
            </div>
            {nlExpanded ? <ChevronUp size={20} color={colors.neutral['500']} /> : <ChevronDown size={20} color={colors.neutral['500']} />}
          </button>

          {/* Expanded content */}
          {nlExpanded && (
            <div style={{ padding: '24px' }}>

              {/* ---- Section 1: Plain-Language Risk Summary (auto-loaded) ---- */}
              <div style={{ marginBottom: '28px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                  <FileText size={18} color={colors.neutral['600']} />
                  <span style={{ fontSize: '15px', fontWeight: 700, color: colors.neutral['700'] }}>Patient Risk Summary</span>
                </div>

                {riskSummaryData ? (
                  <div
                    style={{
                      padding: '20px 24px',
                      backgroundColor:
                        riskSummaryData.risk_level === 'critical' || riskSummaryData.risk_level === 'high'
                          ? colors.critical.background
                          : riskSummaryData.risk_level === 'moderate'
                          ? colors.warning.background
                          : colors.stable.background,
                      border: `1px solid ${
                        riskSummaryData.risk_level === 'critical' || riskSummaryData.risk_level === 'high'
                          ? colors.critical.border
                          : riskSummaryData.risk_level === 'moderate'
                          ? colors.warning.border
                          : colors.stable.border
                      }`,
                      borderRadius: '10px',
                    }}
                  >
                    {/* Summary text */}
                    <p style={{ ...typography.body, lineHeight: '1.7', color: colors.neutral['800'], margin: '0 0 16px 0', fontSize: '15px' }}>
                      {riskSummaryData.plain_summary}
                    </p>

                    {/* Metadata row */}
                    <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' as const }}>
                      <div>
                        <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Risk Score: </span>
                        <span style={{ fontWeight: 700, color: colors.neutral['700'] }}>
                          {(riskSummaryData.risk_score * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div>
                        <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Level: </span>
                        <span style={{
                          fontWeight: 700,
                          textTransform: 'capitalize' as const,
                          color:
                            riskSummaryData.risk_level === 'critical' || riskSummaryData.risk_level === 'high'
                              ? colors.critical.text
                              : riskSummaryData.risk_level === 'moderate'
                              ? colors.warning.text
                              : colors.stable.text,
                        }}>
                          {riskSummaryData.risk_level}
                        </span>
                      </div>
                      {riskSummaryData.assessment_date && (
                        <div>
                          <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Assessed: </span>
                          <span style={{ fontWeight: 600, color: colors.neutral['600'] }}>
                            {new Date(riskSummaryData.assessment_date).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div
                    style={{
                      padding: '20px',
                      textAlign: 'center',
                      backgroundColor: colors.neutral['50'],
                      borderRadius: '8px',
                      color: colors.neutral['500'],
                    }}
                  >
                    No risk assessment available for this patient yet.
                  </div>
                )}
              </div>

              {/* Divider */}
              <div style={{ height: '1px', backgroundColor: colors.neutral['200'], marginBottom: '28px' }} />

              {/* ---- Section 2: Alert Preview Generator (interactive) ---- */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                  <Bell size={18} color={colors.neutral['600']} />
                  <span style={{ fontSize: '15px', fontWeight: 700, color: colors.neutral['700'] }}>Alert Preview Generator</span>
                  <span style={{ ...typography.caption, color: colors.neutral['400'] }}>— Preview what this patient would see</span>
                </div>

                {/* Controls row */}
                <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' as const }}>
                  {/* Alert type select */}
                  <div style={{ flex: '1 1 200px' }}>
                    <label style={{ ...typography.caption, color: colors.neutral['500'], display: 'block', marginBottom: '4px' }}>Alert Type</label>
                    <select
                      value={nlAlertType}
                      onChange={(e) => { setNlAlertType(e.target.value); setNlAlertResult(null); }}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: `1px solid ${colors.neutral['300']}`,
                        fontSize: '14px',
                        backgroundColor: colors.neutral.white,
                        color: colors.neutral['700'],
                      }}
                    >
                      <option value="high_heart_rate">High Heart Rate</option>
                      <option value="low_heart_rate">Low Heart Rate</option>
                      <option value="low_spo2">Low SpO₂</option>
                      <option value="high_blood_pressure">High Blood Pressure</option>
                      <option value="irregular_rhythm">Irregular Rhythm</option>
                      <option value="abnormal_activity">Abnormal Activity</option>
                    </select>
                  </div>

                  {/* Severity select */}
                  <div style={{ flex: '1 1 160px' }}>
                    <label style={{ ...typography.caption, color: colors.neutral['500'], display: 'block', marginBottom: '4px' }}>Severity</label>
                    <select
                      value={nlSeverity}
                      onChange={(e) => { setNlSeverity(e.target.value); setNlAlertResult(null); }}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: `1px solid ${colors.neutral['300']}`,
                        fontSize: '14px',
                        backgroundColor: colors.neutral.white,
                        color: colors.neutral['700'],
                      }}
                    >
                      <option value="info">Info</option>
                      <option value="warning">Warning</option>
                      <option value="critical">Critical</option>
                      <option value="emergency">Emergency</option>
                    </select>
                  </div>

                  {/* Generate button */}
                  <div style={{ flex: '0 0 auto', display: 'flex', alignItems: 'flex-end' }}>
                    <button
                      onClick={async () => {
                        if (!patientId) return;
                        setNlAlertLoading(true);
                        setNlAlertResult(null);
                        try {
                          const res = await api.generateNaturalLanguageAlert(
                            Number(patientId),
                            nlAlertType,
                            nlSeverity,
                            undefined,
                            undefined,
                            riskAssessment?.risk_score,
                            riskAssessment?.risk_level
                          );
                          setNlAlertResult(res);
                        } catch (e) {
                          console.error('NL alert generation failed:', e);
                        } finally {
                          setNlAlertLoading(false);
                        }
                      }}
                      disabled={nlAlertLoading}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '8px 20px',
                        backgroundColor: nlAlertLoading ? colors.neutral['300'] : colors.primary.default,
                        color: colors.neutral.white,
                        border: 'none',
                        borderRadius: '8px',
                        cursor: nlAlertLoading ? 'not-allowed' : 'pointer',
                        fontWeight: 600,
                        fontSize: '14px',
                        transition: 'all 0.15s',
                      }}
                    >
                      {nlAlertLoading ? (
                        <><Loader size={15} /> Generating...</>
                      ) : (
                        <><Send size={15} /> Generate Preview</>
                      )}
                    </button>
                  </div>
                </div>

                {/* Generated alert preview */}
                {nlAlertResult && (
                  <div
                    style={{
                      padding: '20px',
                      backgroundColor:
                        nlAlertResult.urgency_level === 'act_now' ? colors.critical.background
                        : nlAlertResult.urgency_level === 'urgent' ? colors.critical.background
                        : nlAlertResult.urgency_level === 'attention_needed' ? colors.warning.background
                        : colors.neutral['50'],
                      border: `1px solid ${
                        nlAlertResult.urgency_level === 'act_now' ? colors.critical.border
                        : nlAlertResult.urgency_level === 'urgent' ? colors.critical.border
                        : nlAlertResult.urgency_level === 'attention_needed' ? colors.warning.border
                        : colors.neutral['200']
                      }`,
                      borderRadius: '10px',
                    }}
                  >
                    {/* Urgency badge */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
                      {nlAlertResult.urgency_level === 'act_now' && <AlertOctagon size={20} color={colors.critical.badge} />}
                      {nlAlertResult.urgency_level === 'urgent' && <AlertTriangle size={20} color={colors.critical.badge} />}
                      {nlAlertResult.urgency_level === 'attention_needed' && <AlertTriangle size={20} color={colors.warning.badge} />}
                      {nlAlertResult.urgency_level === 'for_your_info' && <Info size={20} color={colors.neutral['500']} />}
                      <span style={{
                        fontSize: '12px',
                        fontWeight: 700,
                        textTransform: 'uppercase' as const,
                        letterSpacing: '0.5px',
                        color:
                          nlAlertResult.urgency_level === 'act_now' || nlAlertResult.urgency_level === 'urgent'
                            ? colors.critical.text
                            : nlAlertResult.urgency_level === 'attention_needed'
                            ? colors.warning.text
                            : colors.neutral['500'],
                      }}>
                        {nlAlertResult.urgency_level.replace(/_/g, ' ')}
                      </span>
                    </div>

                    {/* Friendly message */}
                    <p style={{ ...typography.body, lineHeight: '1.7', color: colors.neutral['800'], margin: '0 0 16px 0', fontSize: '15px' }}>
                      {nlAlertResult.friendly_message}
                    </p>

                    {/* Action steps */}
                    {nlAlertResult.action_steps.length > 0 && (
                      <div style={{ marginBottom: '14px' }}>
                        <div style={{ ...typography.caption, fontWeight: 600, color: colors.neutral['500'], marginBottom: '8px' }}>
                          Recommended Actions:
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {nlAlertResult.action_steps.map((step, i) => (
                            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                              <span style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '20px',
                                height: '20px',
                                borderRadius: '50%',
                                backgroundColor: colors.primary.default,
                                color: colors.neutral.white,
                                fontSize: '11px',
                                fontWeight: 700,
                                flexShrink: 0,
                                marginTop: '2px',
                              }}>
                                {i + 1}
                              </span>
                              <span style={{ ...typography.body, color: colors.neutral['700'] }}>{step}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Risk context */}
                    {nlAlertResult.risk_context && (
                      <div style={{
                        padding: '10px 14px',
                        backgroundColor: 'rgba(255,255,255,0.5)',
                        borderRadius: '6px',
                        ...typography.caption,
                        color: colors.neutral['600'],
                        fontStyle: 'italic',
                      }}>
                        {nlAlertResult.risk_context}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* Advanced ML: Model Management Panel (Endpoints 9 & 10)          */}
        {/* ================================================================= */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            marginBottom: '32px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            overflow: 'hidden',
          }}
        >
          {/* Collapsible header */}
          <button
            onClick={() => setModelExpanded(!modelExpanded)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '20px 24px',
              backgroundColor: colors.neutral.white,
              border: 'none',
              cursor: 'pointer',
              borderBottom: modelExpanded ? `1px solid ${colors.neutral['300']}` : 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Cpu size={22} color={colors.primary.default} />
              <span style={{ ...typography.sectionTitle, margin: 0 }}>ML Model Management</span>
              {retrainReadiness && (
                <span
                  style={{
                    backgroundColor: retrainReadiness.ready ? colors.stable.badge : colors.neutral['200'],
                    color: retrainReadiness.ready ? colors.neutral.white : colors.neutral['600'],
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '2px 10px',
                    borderRadius: '12px',
                  }}
                >
                  {retrainReadiness.ready ? 'Ready to retrain' : 'Not ready'}
                </span>
              )}
            </div>
            {modelExpanded ? <ChevronUp size={20} color={colors.neutral['500']} /> : <ChevronDown size={20} color={colors.neutral['500']} />}
          </button>

          {/* Expanded content */}
          {modelExpanded && (
            <div style={{ padding: '24px' }}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: '20px',
                }}
              >
                {/* Model Status Card */}
                <div
                  style={{
                    padding: '20px',
                    backgroundColor: colors.neutral['50'],
                    borderRadius: '10px',
                    border: `1px solid ${colors.neutral['200']}`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <HardDrive size={18} color={colors.neutral['600']} />
                    <span style={{ fontSize: '15px', fontWeight: 700, color: colors.neutral['700'] }}>Model Status</span>
                  </div>

                  {retrainStatus ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {/* Artifact indicators */}
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' as const }}>
                        {[{ label: 'Model', ok: retrainStatus.model_exists }, { label: 'Scaler', ok: retrainStatus.scaler_exists }, { label: 'Features', ok: retrainStatus.features_exists }].map((item) => (
                          <span
                            key={item.label}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '3px 10px',
                              borderRadius: '6px',
                              fontSize: '12px',
                              fontWeight: 600,
                              backgroundColor: item.ok ? colors.stable.background : colors.critical.background,
                              color: item.ok ? colors.stable.text : colors.critical.text,
                              border: `1px solid ${item.ok ? colors.stable.border : colors.critical.border}`,
                            }}
                          >
                            {item.ok ? <CheckCircle size={12} /> : <XCircle size={12} />}
                            {item.label}
                          </span>
                        ))}
                      </div>

                      {/* Metadata */}
                      {retrainStatus.metadata && (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '8px' }}>
                          <div>
                            <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Algorithm: </span>
                            <span style={{ ...typography.body, fontWeight: 600 }}>{retrainStatus.metadata.model_name}</span>
                          </div>
                          <div>
                            <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Version: </span>
                            <span style={{ ...typography.body, fontWeight: 600 }}>{retrainStatus.metadata.version}</span>
                          </div>
                          <div>
                            <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Accuracy: </span>
                            <span style={{ ...typography.body, fontWeight: 700, color: colors.stable.text }}>{retrainStatus.metadata.accuracy}</span>
                          </div>
                          {retrainStatus.model_size_bytes && (
                            <div>
                              <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Size: </span>
                              <span style={{ ...typography.body, fontWeight: 600 }}>{(retrainStatus.model_size_bytes / 1024).toFixed(0)} KB</span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Last modified */}
                      {retrainStatus.model_modified && (
                        <div style={{ ...typography.caption, color: colors.neutral['400'], marginTop: '4px' }}>
                          Last modified: {new Date(retrainStatus.model_modified).toLocaleString()}
                        </div>
                      )}
                      {retrainStatus.metadata?.note && (
                        <div style={{ ...typography.caption, color: colors.neutral['400'], fontStyle: 'italic' }}>
                          {retrainStatus.metadata.note}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ ...typography.body, color: colors.neutral['400'] }}>Unable to load model status.</div>
                  )}
                </div>

                {/* Retraining Readiness Card */}
                <div
                  style={{
                    padding: '20px',
                    backgroundColor: retrainReadiness?.ready ? colors.stable.background : colors.neutral['50'],
                    borderRadius: '10px',
                    border: `1px solid ${retrainReadiness?.ready ? colors.stable.border : colors.neutral['200']}`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <RefreshCw size={18} color={retrainReadiness?.ready ? colors.stable.text : colors.neutral['600']} />
                    <span style={{ fontSize: '15px', fontWeight: 700, color: colors.neutral['700'] }}>Retraining Readiness</span>
                  </div>

                  {retrainReadiness ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {/* Records progress */}
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Records</span>
                          <span style={{ ...typography.body, fontWeight: 700, fontSize: '13px' }}>
                            {retrainReadiness.new_records} / {retrainReadiness.min_records_required}
                          </span>
                        </div>
                        <div style={{ height: '8px', backgroundColor: colors.neutral['100'], borderRadius: '4px', overflow: 'hidden' }}>
                          <div
                            style={{
                              height: '100%',
                              width: `${Math.min(100, (retrainReadiness.new_records / retrainReadiness.min_records_required) * 100)}%`,
                              backgroundColor: retrainReadiness.new_records >= retrainReadiness.min_records_required ? colors.stable.badge : colors.warning.badge,
                              borderRadius: '4px',
                              transition: 'width 0.5s ease',
                            }}
                          />
                        </div>
                      </div>

                      {/* Last retrain */}
                      <div>
                        <span style={{ ...typography.caption, color: colors.neutral['500'] }}>Last retrain: </span>
                        <span style={{ ...typography.body, fontWeight: 600 }}>
                          {retrainReadiness.last_retrain_date
                            ? new Date(retrainReadiness.last_retrain_date).toLocaleDateString()
                            : 'Never'}
                        </span>
                        <span style={{ ...typography.caption, color: colors.neutral['400'] }}>
                          {' '}(min {retrainReadiness.min_days_between_retrains} days between)
                        </span>
                      </div>

                      {/* Reasons */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {retrainReadiness.reasons.map((reason, i) => (
                          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            {retrainReadiness.ready
                              ? <CheckCircle size={14} color={colors.stable.text} />
                              : <Info size={14} color={colors.neutral['400']} />
                            }
                            <span style={{ ...typography.caption, color: colors.neutral['600'] }}>{reason}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div style={{ ...typography.body, color: colors.neutral['400'] }}>Unable to load readiness check.</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* Advanced ML: Prediction Explainability Panel (Endpoint 11)       */}
        {/* ================================================================= */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            marginBottom: '32px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            overflow: 'hidden',
          }}
        >
          {/* Collapsible header */}
          <button
            onClick={() => setExplainExpanded(!explainExpanded)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '20px 24px',
              backgroundColor: colors.neutral.white,
              border: 'none',
              cursor: 'pointer',
              borderBottom: explainExpanded ? `1px solid ${colors.neutral['300']}` : 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Search size={22} color={colors.primary.default} />
              <span style={{ ...typography.sectionTitle, margin: 0 }}>Prediction Explainability</span>
              {explainData && (
                <span
                  style={{
                    backgroundColor:
                      explainData.risk_level === 'high' || explainData.risk_level === 'critical'
                        ? colors.critical.background
                        : explainData.risk_level === 'moderate'
                        ? colors.warning.background
                        : colors.stable.background,
                    color:
                      explainData.risk_level === 'high' || explainData.risk_level === 'critical'
                        ? colors.critical.text
                        : explainData.risk_level === 'moderate'
                        ? colors.warning.text
                        : colors.stable.text,
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '2px 10px',
                    borderRadius: '12px',
                    textTransform: 'capitalize' as const,
                  }}
                >
                  {explainData.risk_level} — {(explainData.risk_score * 100).toFixed(0)}%
                </span>
              )}
            </div>
            {explainExpanded ? <ChevronUp size={20} color={colors.neutral['500']} /> : <ChevronDown size={20} color={colors.neutral['500']} />}
          </button>

          {/* Expanded content */}
          {explainExpanded && (
            <div style={{ padding: '24px' }}>
              {/* Run button — uses patient's current data */}
              <div style={{ marginBottom: '20px' }}>
                <button
                  onClick={async () => {
                    if (!patient || !latestVitals) return;
                    setExplainLoading(true);
                    setExplainData(null);
                    try {
                      const res = await api.explainPrediction({
                        age: patient.age ?? 55,
                        baseline_hr: patient.baseline_hr ?? 72,
                        max_safe_hr: patient.max_safe_hr ?? 165,
                        avg_heart_rate: latestVitals.heart_rate ?? 85,
                        peak_heart_rate: Math.round((latestVitals.heart_rate ?? 85) * 1.2),
                        min_heart_rate: Math.round((latestVitals.heart_rate ?? 85) * 0.8),
                        avg_spo2: latestVitals.spo2 ?? 97,
                        duration_minutes: 20,
                        recovery_time_minutes: 5,
                        activity_type: 'walking',
                      });
                      setExplainData(res);
                    } catch (e: any) {
                      console.error('Explain prediction failed:', e);
                      // Check if it's a 503 error (model not loaded)
                      if (e?.response?.status === 503) {
                        alert('ML model not loaded on backend. Please check backend logs and restart with model files present in ml_models/ folder.');
                      } else {
                        alert(`Failed to explain prediction: ${e?.response?.data?.detail || e.message || 'Unknown error'}`);
                      }
                    } finally {
                      setExplainLoading(false);
                    }
                  }}
                  disabled={explainLoading || !patient || !latestVitals}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 24px',
                    backgroundColor: explainLoading ? colors.neutral['300'] : colors.primary.default,
                    color: colors.neutral.white,
                    border: 'none',
                    borderRadius: '8px',
                    cursor: explainLoading || !patient ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    fontSize: '14px',
                    transition: 'all 0.15s',
                  }}
                >
                  {explainLoading ? (
                    <><Loader size={16} /> Analyzing...</>
                  ) : (
                    <><Search size={16} /> Explain Risk Using Latest Vitals</>
                  )}
                </button>
                <div style={{ ...typography.caption, color: colors.neutral['400'], marginTop: '6px' }}>
                  Uses patient’s current vitals and profile to run a prediction with feature importance analysis.
                </div>
              </div>

              {/* Explanation results */}
              {explainData && (
                <>
                  {/* Plain explanation */}
                  <div
                    style={{
                      padding: '18px 22px',
                      backgroundColor:
                        explainData.risk_level === 'high' || explainData.risk_level === 'critical'
                          ? colors.critical.background
                          : explainData.risk_level === 'moderate'
                          ? colors.warning.background
                          : colors.stable.background,
                      border: `1px solid ${
                        explainData.risk_level === 'high' || explainData.risk_level === 'critical'
                          ? colors.critical.border
                          : explainData.risk_level === 'moderate'
                          ? colors.warning.border
                          : colors.stable.border
                      }`,
                      borderRadius: '10px',
                      marginBottom: '20px',
                    }}
                  >
                    <p style={{ ...typography.body, lineHeight: '1.7', color: colors.neutral['800'], margin: 0, fontSize: '15px' }}>
                      {explainData.plain_explanation}
                    </p>
                  </div>

                  {/* Top contributing features */}
                  <div style={{ marginBottom: '8px' }}>
                    <div style={{ ...typography.caption, fontWeight: 700, color: colors.neutral['500'], marginBottom: '12px' }}>
                      Top Contributing Features
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {explainData.feature_importance.top_features.map((feat, idx) => {
                        const isIncreasing = feat.direction === 'increasing';
                        const isDecreasing = feat.direction === 'decreasing';
                        const barWidth = Math.min(100, Math.abs(feat.contribution) * 500);
                        return (
                          <div
                            key={idx}
                            style={{
                              padding: '14px 18px',
                              backgroundColor: colors.neutral['50'],
                              borderRadius: '8px',
                              border: `1px solid ${colors.neutral['200']}`,
                            }}
                          >
                            {/* Feature header row */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  width: '24px',
                                  height: '24px',
                                  borderRadius: '50%',
                                  backgroundColor:
                                    isIncreasing ? colors.critical.background
                                    : isDecreasing ? colors.stable.background
                                    : colors.neutral['100'],
                                  border: `1px solid ${
                                    isIncreasing ? colors.critical.border
                                    : isDecreasing ? colors.stable.border
                                    : colors.neutral['200']
                                  }`,
                                }}>
                                  {isIncreasing && <ArrowUpRight size={14} color={colors.critical.text} />}
                                  {isDecreasing && <ArrowDownRight size={14} color={colors.stable.text} />}
                                  {!isIncreasing && !isDecreasing && <Minus size={14} color={colors.neutral['400']} />}
                                </span>
                                <span style={{ fontWeight: 700, fontSize: '14px', color: colors.neutral['800'] }}>
                                  {feat.feature.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                </span>
                              </div>
                              <span style={{
                                fontWeight: 700,
                                fontSize: '14px',
                                color: isIncreasing ? colors.critical.text : isDecreasing ? colors.stable.text : colors.neutral['500'],
                              }}>
                                {feat.value}
                              </span>
                            </div>

                            {/* Contribution bar */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                              <div style={{ flex: 1, height: '6px', backgroundColor: colors.neutral['100'], borderRadius: '3px', overflow: 'hidden' }}>
                                <div
                                  style={{
                                    height: '100%',
                                    width: `${barWidth}%`,
                                    backgroundColor: isIncreasing ? colors.critical.badge : isDecreasing ? colors.stable.badge : colors.neutral['300'],
                                    borderRadius: '3px',
                                    transition: 'width 0.4s ease',
                                  }}
                                />
                              </div>
                              <span style={{ ...typography.caption, color: colors.neutral['500'], minWidth: '50px', textAlign: 'right' }}>
                                {(feat.contribution * 100).toFixed(1)}%
                              </span>
                            </div>

                            {/* Explanation */}
                            <div style={{ ...typography.caption, color: colors.neutral['500'] }}>
                              {feat.explanation}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Method badge */}
                  <div style={{ ...typography.caption, color: colors.neutral['400'], marginTop: '12px' }}>
                    Method: {explainData.feature_importance.method.replace(/_/g, ' ')} • {explainData.feature_importance.feature_count} features analyzed
                  </div>
                </>
              )}

              {/* Empty state when no analysis run yet */}
              {!explainData && !explainLoading && (
                <div
                  style={{
                    padding: '24px',
                    textAlign: 'center',
                    backgroundColor: colors.neutral['50'],
                    borderRadius: '8px',
                    color: colors.neutral['500'],
                  }}
                >
                  Click the button above to run a prediction explanation using this patient’s latest vitals.
                </div>
              )}
            </div>
          )}
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
                    <div
                      key={alert.alert_id}
                      style={{ padding: '12px', backgroundColor: bg, borderRadius: '8px' }}
                    >
                      <div style={{ ...typography.body, color: text, fontWeight: 600 }}>
                        ● {alert.severity.toUpperCase()}: {alert.title || alert.alert_type.replaceAll('_', ' ')}
                      </div>
                      <div style={{ ...typography.caption, color: text, marginTop: '4px' }}>
                        {formatTimeAgo(alert.created_at)}
                      </div>
                    </div>
                  );
                })
              )}
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
              {activities.length === 0 ? (
                <div style={{ padding: '12px', backgroundColor: colors.neutral['50'], borderRadius: '8px' }}>
                  <div style={{ ...typography.body, fontWeight: 600 }}>No sessions yet</div>
                </div>
              ) : (
                activities.map((session) => (
                  <div
                    key={session.session_id}
                    style={{ padding: '12px', backgroundColor: colors.neutral['50'], borderRadius: '8px' }}
                  >
                    <div style={{ ...typography.body, fontWeight: 600 }}>
                      {new Date(session.start_time).toLocaleDateString()}: {session.duration_minutes ?? '--'}-min{' '}
                      {session.activity_type.replaceAll('_', ' ')}
                    </div>
                    <div style={{ ...typography.caption, color: colors.neutral['500'], marginTop: '4px' }}>
                      Avg HR: {session.avg_heart_rate ?? '--'} BPM • Recovery: {session.recovery_time_minutes ?? '--'} min
                    </div>
                  </div>
                ))
              )}
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
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <AlertTriangle size={20} color={colors.critical.text} />
              <h3 style={{ ...typography.sectionTitle, color: colors.critical.text, margin: 0 }}>
                AI Risk Assessment
              </h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
              <button
                onClick={handleComputeRisk}
                disabled={computingRisk}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  backgroundColor: colors.primary.default,
                  color: colors.neutral.white,
                  border: 'none',
                  borderRadius: '8px',
                  cursor: computingRisk ? 'not-allowed' : 'pointer',
                  fontWeight: 500,
                  fontSize: '13px',
                  opacity: computingRisk ? 0.7 : 1,
                }}
              >
                <RefreshCw size={14} />
                {computingRisk ? 'Computing...' : riskAssessment ? 'Recompute' : 'Run AI Assessment'}
              </button>
              <p style={{ fontSize: '11px', color: colors.neutral['500'], margin: 0 }}>
                Requires vitals submitted within the last 30 minutes.
              </p>
            </div>
          </div>

          {computeRiskMessage && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: '8px',
                marginBottom: '12px',
                border: `1px solid ${computeRiskMessage.type === 'success' ? colors.stable.border : colors.warning.border}`,
                backgroundColor: computeRiskMessage.type === 'success' ? colors.stable.background : colors.warning.background,
                color: computeRiskMessage.type === 'success' ? colors.stable.text : colors.warning.text,
                fontSize: '13px',
                fontWeight: 500,
              }}
            >
              {computeRiskMessage.text}
            </div>
          )}

          <div style={{ marginBottom: '16px' }}>
            <div style={{ ...typography.body, color: colors.critical.text, marginBottom: '8px' }}>
              <strong>
                Current Risk: {riskAssessment?.risk_level?.toUpperCase() || 'N/A'} ({(riskAssessment?.risk_score ?? 0).toFixed(2)})
              </strong>
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ ...typography.body, color: colors.critical.text, fontWeight: 600, marginBottom: '8px' }}>
              Contributing Factors:
            </div>
            <ul style={{ margin: 0, paddingLeft: '20px' }}>
              {riskFactors.length === 0 ? (
                <li style={{ ...typography.body, color: colors.critical.text, marginBottom: '4px' }}>
                  No contributing factors available.
                </li>
              ) : (
                riskFactors.map((factor, idx) => (
                  <li key={idx} style={{ ...typography.body, color: colors.critical.text, marginBottom: '4px' }}>
                    {factor}
                  </li>
                ))
              )}
            </ul>
          </div>

          <div style={{ paddingTop: '16px', borderTop: `1px solid ${colors.critical.border}` }}>
            <div style={{ ...typography.body, color: colors.critical.text, fontWeight: 600 }}>
              Recommendation:
            </div>
            <div style={{ ...typography.body, color: colors.critical.text, marginTop: '8px' }}>
              {recommendation?.description || recommendation?.warnings || 'No recommendation available.'}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default PatientDetailPage;
