/*
Dashboard page.

Main view for clinicians. Shows overall statistics:
- How many patients are being monitored
- How many have critical alerts right now
- Monitoring coverage and risk status
- Charts showing patient-level trends

Also shows a list of recent alerts that need attention.
*/

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  Heart,
  AlertTriangle,
} from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { api } from '../services/api';
import { AlertResponse, AlertStatsResponse, PendingConsentRequest, User, VitalSignResponse } from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';
import StatCard from '../components/cards/StatCard';
import ClinicianTopBar from '../components/common/ClinicianTopBar';

// Base URL for the backend API and whether live alert push (SSE) is enabled
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://api.back-adaptivhealthuowd.xyz';
const ENABLE_ALERT_PUSH = process.env.REACT_APP_ENABLE_ALERT_PUSH === 'true';

// Top-level stats shown on the dashboard cards
interface Stats {
  totalPatients: number;
  activeMonitoring: number;
  criticalAlerts: number;
}

// Summary of how many patients sent readings in the last 24 hours
interface MonitoringSummary {
  patientsWithReadings24h: number;
  patientsWithoutReadings24h: number;
  totalReadings24h: number;
  highOrCriticalRiskPatients: number;
}

interface HrTrendSeries {
  key: string;
  label: string;
  color: string;
}

interface HrTrendPoint {
  day: string;
  [seriesKey: string]: string | number | null;
}

const toRecord = (value: unknown): Record<string, unknown> => {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
};

const getHttpStatus = (error: unknown): number | undefined => {
  const record = toRecord(error);
  const response = toRecord(record.response);
  const status = response.status;
  return typeof status === 'number' ? status : undefined;
};

// Normalize the alert stats response from the API into a consistent shape
const normalizeAlertStats = (raw: unknown): AlertStatsResponse => {
  const rawRecord = toRecord(raw);
  const inputSeverity = toRecord(rawRecord.by_severity ?? rawRecord.severity_breakdown);
  const bySeverity: Record<string, number> = {};

  Object.entries(inputSeverity).forEach(([key, value]) => {
    const normalizedKey = String(key).toLowerCase();
    const numericValue = Number(value);
    bySeverity[normalizedKey] = Number.isFinite(numericValue) ? numericValue : 0;
  });

  const totalFromSeverity = Object.values(bySeverity).reduce((sum, count) => sum + Number(count || 0), 0);
  const totalCandidate = Number(rawRecord.total);
  const total = Number.isFinite(totalCandidate) ? totalCandidate : totalFromSeverity;

  return {
    total,
    by_severity: bySeverity,
    by_type: toRecord(rawRecord.by_type) as Record<string, number>,
    unacknowledged_count: Number(rawRecord.unacknowledged_count ?? 0),
  };
};

// Ordered weekday labels for chart x-axis
const WEEKDAY_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const toWeekdayLabel = (timestamp?: string): string => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-US', { weekday: 'short' });
};

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();

  // Overview numbers (patient count, monitoring, critical alerts)
  const [stats, setStats] = useState<Stats>({
    totalPatients: 0,
    activeMonitoring: 0,
    criticalAlerts: 0,
  });
  // Page-level state
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [alertStats, setAlertStats] = useState<AlertStatsResponse | null>(null);
  // Five most recent alerts shown in the bottom widget
  const [recentAlerts, setRecentAlerts] = useState<AlertResponse[]>([]);
  const [dataWarning, setDataWarning] = useState<string | null>(null);
  // Consent requests a clinician still needs to approve
  const [pendingConsent, setPendingConsent] = useState<PendingConsentRequest[]>([]);
  // 24-hour monitoring coverage stats
  const [monitoringSummary, setMonitoringSummary] = useState<MonitoringSummary>({
    patientsWithReadings24h: 0,
    patientsWithoutReadings24h: 0,
    totalReadings24h: 0,
    highOrCriticalRiskPatients: 0,
  });
  // Heart-rate trend line-chart data (top 5 highest-risk patients)
  const [hrTrendData, setHrTrendData] = useState<HrTrendPoint[]>([]);
  const [hrTrendSeries, setHrTrendSeries] = useState<HrTrendSeries[]>([]);
  // Bar chart: how many patients fall into each risk bucket
  const [healthScoreData, setHealthScoreData] = useState<
    Array<{ range: string; count: number }>
  >([]);

  // Load everything when the page first opens
  useEffect(() => {
    loadDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refresh just the alert widgets (called by polling, SSE, and focus events)
  const refreshAlertWidgets = async (): Promise<boolean> => {
    try {
      const [statsResponse, alertsResponse] = await Promise.all([
        api.getAlertStats(),
        api.getAlerts(1, 5),
      ]);

      const normalizedStats = normalizeAlertStats(statsResponse ?? {});
      setAlertStats(normalizedStats);
      setRecentAlerts(alertsResponse?.alerts ?? []);

      const criticalCount =
        Number(normalizedStats.by_severity?.critical ?? 0) +
        Number(normalizedStats.by_severity?.emergency ?? 0);

      setStats((prev) => ({
        ...prev,
        criticalAlerts: criticalCount,
      }));
      return true;
    } catch (error) {
      const status = getHttpStatus(error);
      if (status === 401) {
        return false;
      }
      console.warn('Could not refresh alert widgets:', error);
      return true;
    }
  };

  // Set up live alert refreshing: poll every second, listen for SSE pushes
  // and window-focus / visibility-change events
  useEffect(() => {
    if (!currentUser) return;

    const onAlertsUpdated = () => {
      void refreshAlertWidgets();
    };

    const onFocus = () => {
      void refreshAlertWidgets();
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        void refreshAlertWidgets();
      }
    };

    let eventSource: EventSource | null = null;

    const token = localStorage.getItem('token');

    const onPushMessage = () => {
      void refreshAlertWidgets();
    };

    const connectSse = () => {
      if (!token || typeof EventSource === 'undefined') {
        return;
      }

      try {
        eventSource = new EventSource(
          `${API_BASE_URL}/api/v1/alerts/stream?token=${encodeURIComponent(token)}`
        );

        eventSource.onopen = () => {
          void refreshAlertWidgets();
        };
        eventSource.onmessage = onPushMessage;
        eventSource.onerror = () => {
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
        };
      } catch {
        eventSource = null;
      }
    };

    window.addEventListener('alerts:updated', onAlertsUpdated);
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibilityChange);

    // Polling fallback remains active; push channel (SSE/WS) triggers instant refreshes.
    const intervalId = window.setInterval(() => {
      void refreshAlertWidgets().then((ok) => {
        if (!ok) {
          window.clearInterval(intervalId);
        }
      });
    }, 1000);

    if (ENABLE_ALERT_PUSH) {
      connectSse();
    }

    return () => {
      window.removeEventListener('alerts:updated', onAlertsUpdated);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.clearInterval(intervalId);
      if (eventSource) {
        eventSource.close();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser?.user_id]);

  // Refresh dashboard data every 60s (batch-sync arrives every 5 min, so 60s is plenty).
  // SSE alert stream already handles instant critical notifications on this page.
  useEffect(() => {
    if (!currentUser) return;

    const intervalId = setInterval(() => {
      loadDashboardData(true);
    }, 60_000);

    return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser?.user_id]);

  // Main data loader: fetches the user, patient list, alert stats, charts.
  // silent=true skips the loading spinner (used by periodic refresh so the UI doesn't flash).
  const loadDashboardData = async (silent = false) => {
    if (!silent) setLoading(true);
    setLoadError(null);
    setDataWarning(null);
    try {
      const withTimeout = async <T,>(promise: Promise<T>, timeoutMs = 12000): Promise<T> => {
        return await Promise.race([
          promise,
          new Promise<T>((_, reject) =>
            setTimeout(() => reject(new Error('Request timed out')), timeoutMs)
          ),
        ]);
      };

      const user = await withTimeout(api.getCurrentUser());
      setCurrentUser(user);

      // If this user is an admin, send them to the admin page instead
      const role = user.user_role;
      if (role === 'admin') {
        navigate('/admin');
        return;
      }

      // Fetch patients, alert stats, and recent alerts in parallel
      const [usersResult, statsResult, alertsResult] =
        await withTimeout(
          Promise.allSettled([
            api.getAllUsers(1, 200),
            api.getAlertStats(),
            api.getAlerts(1, 5),
          ])
        );

      // Load pending consent requests for clinicians
      if (role === 'clinician') {
        try {
          const consentResp = await withTimeout(api.getPendingConsentRequests());
          setPendingConsent(consentResp.pending_requests || []);
        } catch (e) {
          console.warn('Could not load consent requests:', e);
        }
      }

      const usersList = usersResult.status === 'fulfilled' ? usersResult.value : null;
      const statsResponse = statsResult.status === 'fulfilled' ? statsResult.value : null;
      const alertsResponse = alertsResult.status === 'fulfilled' ? alertsResult.value : null;

      const failedWidgets: string[] = [];
      if (usersResult.status === 'rejected') failedWidgets.push('patients');
      if (statsResult.status === 'rejected') failedWidgets.push('alert stats');
      if (alertsResult.status === 'rejected') failedWidgets.push('alerts');
      if (failedWidgets.length > 0) {
        setDataWarning(`Some dashboard widgets could not load: ${failedWidgets.join(', ')}.`);
      }

      const normalizedStats = normalizeAlertStats(statsResponse ?? {});

      setCurrentUser(user);
      setAlertStats(normalizedStats);
      setRecentAlerts(alertsResponse?.alerts ?? []);

      const activeCount = usersList?.users?.filter((u) => u.is_active).length ?? 0;
      const criticalCount =
        Number(normalizedStats.by_severity?.critical ?? 0) +
        Number(normalizedStats.by_severity?.emergency ?? 0);

      setStats({
        totalPatients: usersList?.total ?? 0,
        activeMonitoring: activeCount,
        criticalAlerts: criticalCount,
      });

      const patientUsers = (usersList?.users ?? []).filter((userItem) => {
        const userRole = (userItem.user_role ?? '').toLowerCase();
        return userRole === 'patient';
      });

      // For each patient, load their 7-day vital history and latest risk score
      if (patientUsers.length > 0) {
        const [historyResults, riskResults] = await Promise.all([
          Promise.allSettled(
            patientUsers.map((patient) => api.getVitalSignsHistoryForUser(patient.user_id, 7, 1, 100))
          ),
          Promise.allSettled(
            patientUsers.map((patient) => api.getLatestRiskAssessmentForUser(patient.user_id))
          ),
        ]);

        // Count how many patients fall in each risk category
        const riskCounts = {
          low: 0,
          moderate: 0,
          high: 0,
          critical: 0,
        };

        const riskRank: Record<string, number> = {
          low: 1,
          moderate: 2,
          high: 3,
          critical: 4,
        };

        const riskByPatientId: Record<number, { level: string; score: number }> = {};

        riskResults.forEach((result, index) => {
          const patientId = patientUsers[index]?.user_id;
          if (!patientId) return;

          const level = result.status === 'fulfilled'
            ? String(result.value?.risk_level ?? 'low').toLowerCase()
            : 'low';
          const riskScore = result.status === 'fulfilled'
            ? Number(result.value?.risk_score ?? 0)
            : 0;
          const normalizedLevel = ['low', 'moderate', 'high', 'critical'].includes(level) ? level : 'low';

          riskByPatientId[patientId] = { level: normalizedLevel, score: riskScore };

          if (normalizedLevel === 'low') riskCounts.low += 1;
          else if (normalizedLevel === 'moderate') riskCounts.moderate += 1;
          else if (normalizedLevel === 'high') riskCounts.high += 1;
          else if (normalizedLevel === 'critical') riskCounts.critical += 1;
        });

        const historyByPatientId: Record<number, VitalSignResponse[]> = {};
        historyResults.forEach((result, index) => {
          const patientId = patientUsers[index]?.user_id;
          if (!patientId) return;
          if (result.status === 'fulfilled') {
            historyByPatientId[patientId] = result.value?.vitals ?? [];
          } else {
            historyByPatientId[patientId] = [];
          }
        });

        // Calculate the 24-hour monitoring coverage numbers
        const nowMs = Date.now();
        let patientsWithReadings24h = 0;
        let totalReadings24h = 0;

        for (const patient of patientUsers) {
          const rows = historyByPatientId[patient.user_id] ?? [];
          const readings24h = rows.filter((row) => {
            if (!row?.timestamp) return false;
            const ts = new Date(row.timestamp).getTime();
            return !Number.isNaN(ts) && nowMs - ts <= 24 * 60 * 60 * 1000;
          });
          if (readings24h.length > 0) {
            patientsWithReadings24h += 1;
            totalReadings24h += readings24h.length;
          }
        }

        setMonitoringSummary({
          patientsWithReadings24h,
          patientsWithoutReadings24h: Math.max(0, patientUsers.length - patientsWithReadings24h),
          totalReadings24h,
          highOrCriticalRiskPatients: riskCounts.high + riskCounts.critical,
        });

        // Build the heart-rate trend chart data for the top 5 highest-risk patients
        const highestRiskPatients = [...patientUsers]
          .map((patient) => ({
            ...patient,
            riskLevel: riskByPatientId[patient.user_id]?.level ?? 'low',
            riskScore: riskByPatientId[patient.user_id]?.score ?? 0,
          }))
          .sort((a, b) => {
            const severityDiff = (riskRank[b.riskLevel] ?? 0) - (riskRank[a.riskLevel] ?? 0);
            if (severityDiff !== 0) return severityDiff;
            return b.riskScore - a.riskScore;
          })
          .slice(0, 5);

        const seriesPalette = [
          colors.critical.badge,
          colors.warning.badge,
          colors.primary.default,
          colors.chart.blue,
          colors.stable.badge,
        ];

        const series: HrTrendSeries[] = highestRiskPatients.map((patient, idx) => ({
          key: `p_${patient.user_id}`,
          label: patient.full_name || `Patient ${patient.user_id}`,
          color: seriesPalette[idx % seriesPalette.length],
        }));

        const lineChartData: HrTrendPoint[] = WEEKDAY_ORDER.map((day) => {
          const row: HrTrendPoint = { day };
          for (const patientSeries of series) {
            const patientId = Number(patientSeries.key.replace('p_', ''));
            const rows = historyByPatientId[patientId] ?? [];
            const dayValues = rows
              .filter((vital) => toWeekdayLabel(vital?.timestamp) === day && typeof vital?.heart_rate === 'number')
              .map((vital) => Number(vital.heart_rate));

            row[patientSeries.key] =
              dayValues.length > 0
                ? Math.round(dayValues.reduce((sum: number, value: number) => sum + value, 0) / dayValues.length)
                : null;
          }
          return row;
        }).filter((row) =>
          series.some((patientSeries) => typeof row[patientSeries.key] === 'number')
        );

        setHrTrendSeries(series);
        setHrTrendData(lineChartData);

        setHealthScoreData([
          { range: 'Low Risk', count: riskCounts.low },
          { range: 'Moderate', count: riskCounts.moderate },
          { range: 'High Risk', count: riskCounts.high },
          { range: 'Critical', count: riskCounts.critical },
        ]);
      } else {
        setMonitoringSummary({
          patientsWithReadings24h: 0,
          patientsWithoutReadings24h: 0,
          totalReadings24h: 0,
          highOrCriticalRiskPatients: 0,
        });
        setHrTrendSeries([]);
        setHrTrendData([]);
        setHealthScoreData([]);
      }
    } catch (error) {
      console.error('Error loading dashboard:', error);
      const message =
        error instanceof Error && error.message === 'Request timed out'
          ? 'The dashboard is taking too long to respond. Please check the backend and try again.'
          : 'We could not load the dashboard. Please make sure the backend is running and try again.';
      setLoadError(message);
    } finally {
      setLoading(false);
    }
  };

  // Format a timestamp as "X min ago" or "X hrs ago"
  const formatTimeAgo = (isoDate?: string) => {
    if (!isoDate) return 'Just now';
    const date = new Date(isoDate);
    const diffMs = Date.now() - date.getTime();
    const diffMin = Math.max(1, Math.floor(diffMs / 60000));
    if (diffMin < 60) return `${diffMin} min ago`;
    const diffHr = Math.floor(diffMin / 60);
    return `${diffHr} hr${diffHr > 1 ? 's' : ''} ago`;
  };

  if (loading) {
    return (
      <div style={{ padding: '32px', textAlign: 'center' }}>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div style={{ padding: '32px', textAlign: 'center' }}>
        <p>{loadError}</p>
        <button
          onClick={() => loadDashboardData()}
          style={{
            marginTop: '12px',
            padding: '8px 16px',
            borderRadius: '6px',
            border: `1px solid ${colors.neutral['300']}`,
            backgroundColor: colors.neutral.white,
            cursor: 'pointer',
            color: colors.neutral['700'],
            fontWeight: 500,
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: colors.neutral['50'],
        fontFamily: '"Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
    >
      <ClinicianTopBar />

      {/* Main Content */}
      <main
        style={{
          maxWidth: '1440px',
          margin: '0 auto',
          padding: '32px',
        }}
      >
        {/* Page Title */}
        <h2 style={typography.pageTitle}>
          Welcome back, {currentUser?.full_name?.split(' ')[0] || 'Doctor'}!
        </h2>
        <p style={{ ...typography.body, color: colors.neutral['500'], marginBottom: '32px' }}>
          Real-time cardiovascular patient monitoring
        </p>

        {dataWarning && (
          <div
            style={{
              backgroundColor: colors.warning.background,
              border: `1px solid ${colors.warning.badge}`,
              borderRadius: '10px',
              padding: '12px 16px',
              marginBottom: '24px',
              color: colors.warning.text,
              fontWeight: 600,
            }}
          >
            {dataWarning}
          </div>
        )}

        {/* Alert Banner (if critical alerts exist) */}
        {stats.criticalAlerts > 0 && (
          <div
            style={{
              backgroundColor: colors.critical.background,
              border: `1px solid ${colors.critical.border}`,
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '32px',
              display: 'flex',
              gap: '12px',
              alignItems: 'flex-start',
            }}
          >
            <AlertTriangle size={20} color={colors.critical.text} strokeWidth={2} />
            <div>
              <div style={{ ...typography.cardTitle, color: colors.critical.text }}>
                Critical Alerts Require Attention
              </div>
              <div style={{ ...typography.body, color: colors.critical.text, marginTop: '4px' }}>
                {stats.criticalAlerts} critical alert(s) need immediate review
              </div>
            </div>
          </div>
        )}

        {/* Stat Cards Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '16px',
            marginBottom: '32px',
          }}
        >
          <StatCard
            icon={Users}
            label="Total Patients"
            value={stats.totalPatients}
            color="primary"
            onClick={() => navigate('/patients')}
          />
          <StatCard
            icon={Heart}
            label="Active Monitoring"
            value={stats.activeMonitoring}
            color="stable"
          />
          <StatCard
            icon={AlertTriangle}
            label="Requires Attention"
            value={alertStats?.unacknowledged_count ?? 0}
            color="warning"
          />
          <StatCard
            icon={AlertTriangle}
            label="Critical Alerts"
            value={stats.criticalAlerts}
            color="critical"
          />
        </div>

        {/* Alert Stats Summary */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            padding: '20px 24px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            marginBottom: '24px',
          }}
        >
          <h3 style={typography.sectionTitle}>Alert Summary</h3>
          <p style={{ ...typography.caption, marginBottom: '16px' }}>Severity breakdown</p>
          {alertStats && alertStats.total > 0 ? (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                gap: '12px',
              }}
            >
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
                <div style={typography.caption}>Total</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>{alertStats.total}</div>
              </div>
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.warning.background }}>
                <div style={typography.caption}>Unacknowledged</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {alertStats.unacknowledged_count}
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.critical.background }}>
                <div style={typography.caption}>Critical</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {alertStats.by_severity?.critical ?? 0}
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.warning.background }}>
                <div style={typography.caption}>Warning</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {alertStats.by_severity?.warning ?? 0}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
              <p style={typography.body}>No alert stats available yet.</p>
            </div>
          )}
        </div>

        {/* Vitals Summary */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            padding: '20px 24px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            marginBottom: '32px',
          }}
        >
          <h3 style={typography.sectionTitle}>Monitoring Summary</h3>
          <p style={{ ...typography.caption, marginBottom: '16px' }}>Operational view (last 24 hours)</p>
          {stats.totalPatients > 0 ? (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                gap: '12px',
              }}
            >
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
                <div style={typography.caption}>Patients with Readings</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {monitoringSummary.patientsWithReadings24h}
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.warning.background }}>
                <div style={typography.caption}>No Readings (24h)</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {monitoringSummary.patientsWithoutReadings24h}
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
                <div style={typography.caption}>Total Readings (24h)</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {monitoringSummary.totalReadings24h}
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.critical.background }}>
                <div style={typography.caption}>High/Critical Risk</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {monitoringSummary.highOrCriticalRiskPatients}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
              <p style={typography.body}>No vitals summary available yet.</p>
            </div>
          )}
        </div>

        {/* Charts Section */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
            gap: '16px',
            marginBottom: '32px',
          }}
        >
          {/* Heart Rate Trend Chart */}
          <div
            style={{
              backgroundColor: colors.neutral.white,
              border: `1px solid ${colors.neutral['300']}`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <h3 style={typography.sectionTitle}>Top 5 Highest-Risk Patients HR Trend</h3>
            <p style={{ ...typography.caption, marginBottom: '16px' }}>Each line is one patient (last 7 days)</p>
            {hrTrendData.length === 0 || hrTrendSeries.length === 0 ? (
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
                <p style={typography.body}>No heart rate trend data yet.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={hrTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.neutral['300']} />
                  <XAxis
                    dataKey="day"
                    stroke={colors.neutral['500']}
                    style={{ fontSize: '12px' }}
                  />
                  <YAxis
                    stroke={colors.neutral['500']}
                    style={{ fontSize: '12px' }}
                    domain={[40, 200]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: colors.neutral.white,
                      border: `1px solid ${colors.neutral['300']}`,
                      borderRadius: '6px',
                    }}
                  />
                  <Legend wrapperStyle={{ paddingTop: '12px' }} />
                  {hrTrendSeries.map((series) => (
                    <Line
                      key={series.key}
                      type="monotone"
                      dataKey={series.key}
                      stroke={series.color}
                      name={series.label}
                      strokeWidth={2}
                      dot={{ fill: series.color, r: 3 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Health Score Distribution */}
          <div
            style={{
              backgroundColor: colors.neutral.white,
              border: `1px solid ${colors.neutral['300']}`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <h3 style={typography.sectionTitle}>Health Score Distribution</h3>
            <p style={{ ...typography.caption, marginBottom: '16px' }}>Population count by risk category</p>
            {healthScoreData.length === 0 ? (
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
                <p style={typography.body}>No risk distribution data yet.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={healthScoreData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.neutral['300']} />
                  <XAxis
                    dataKey="range"
                    stroke={colors.neutral['500']}
                    style={{ fontSize: '12px' }}
                  />
                  <YAxis
                    stroke={colors.neutral['500']}
                    style={{ fontSize: '12px' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: colors.neutral.white,
                      border: `1px solid ${colors.neutral['300']}`,
                      borderRadius: '6px',
                    }}
                  />
                  <Bar
                    dataKey="count"
                    fill={colors.chart.blue}
                    name="Patient Count"
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Recent Activity Feed */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            marginBottom: '32px',
          }}
        >
          <h3 style={typography.sectionTitle}>Recent Activity</h3>
          <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {recentAlerts.length === 0 ? (
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
                <p style={typography.body}>No recent alerts.</p>
              </div>
            ) : (
              recentAlerts.map((alert) => (
                <div
                  key={alert.alert_id}
                  style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}
                >
                  <p style={typography.body}>
                    • {alert.title || alert.alert_type.replaceAll('_', ' ')} ({formatTimeAgo(alert.created_at)})
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Pending Consent Requests (Clinician only) */}
        {pendingConsent.length > 0 && (
          <div
            style={{
              backgroundColor: colors.neutral.white,
              border: `1px solid ${colors.warning.border}`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
              marginBottom: '32px',
            }}
          >
            <h3 style={{ ...typography.sectionTitle, color: colors.warning.text }}>
              Pending Consent Requests ({pendingConsent.length})
            </h3>
            <p style={{ ...typography.caption, marginBottom: '16px' }}>
              These patients have requested to disable data sharing. Review each request.
            </p>
            {pendingConsent.map((req) => (
              <div
                key={req.user_id}
                style={{
                  padding: '12px 16px', borderRadius: '8px', backgroundColor: colors.warning.background,
                  marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ ...typography.body, fontWeight: 600 }}>
                    {req.full_name || req.email} — Opt-out requested (pending approval)
                  </div>
                  {req.reason && <div style={typography.caption}>Reason: {req.reason}</div>}
                  {req.requested_at && <div style={typography.caption}>Requested: {new Date(req.requested_at).toLocaleString()}</div>}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={async () => {
                      await api.reviewConsentRequest(req.user_id, 'approve');
                      setPendingConsent(prev => prev.filter(p => p.user_id !== req.user_id));
                    }}
                    style={{
                      padding: '6px 14px', borderRadius: '6px', border: 'none',
                      backgroundColor: colors.stable.badge, color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: '12px',
                    }}
                  >
                    Approve
                  </button>
                  <button
                    onClick={async () => {
                      await api.reviewConsentRequest(req.user_id, 'reject');
                      setPendingConsent(prev => prev.filter(p => p.user_id !== req.user_id));
                    }}
                    style={{
                      padding: '6px 14px', borderRadius: '6px', border: 'none',
                      backgroundColor: colors.critical.badge, color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: '12px',
                    }}
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Backend Status */}
        <div
          style={{
            backgroundColor: colors.primary.ultralight,
            border: `1px solid ${colors.primary.light}`,
            borderRadius: '12px',
            padding: '20px',
          }}
        >
          <p style={{ ...typography.body, margin: '0 0 8px 0' }}>
            <strong>Backend Status:</strong> Connected to http://localhost:8080
          </p>
          <p style={{ ...typography.caption, margin: 0 }}>
            API Documentation: Visit http://localhost:8080/docs for interactive testing
          </p>
        </div>
      </main>
    </div>
  );
};

export default DashboardPage;
