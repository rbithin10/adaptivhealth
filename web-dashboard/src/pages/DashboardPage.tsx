/*
Dashboard page.

Main view for clinicians. Shows overall statistics:
- How many patients are being monitored
- How many have critical alerts right now
- Average heart rate across all patients
- Charts showing trends

Also shows a list of recent alerts that need attention.
*/

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  Heart,
  AlertTriangle,
  LogOut,
  MessageSquare,
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
import { AlertResponse, AlertStatsResponse, User, VitalSignsSummary } from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';
import StatCard from '../components/cards/StatCard';

interface Stats {
  totalPatients: number;
  activeMonitoring: number;
  criticalAlerts: number;
  avgHeartRate: number;
}

const WEEKDAY_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const toWeekdayLabel = (timestamp?: string): string => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-US', { weekday: 'short' });
};

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats>({
    totalPatients: 0,
    activeMonitoring: 0,
    criticalAlerts: 0,
    avgHeartRate: 72,
  });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [alertStats, setAlertStats] = useState<AlertStatsResponse | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<AlertResponse[]>([]);
  const [vitalsSummary, setVitalsSummary] = useState<VitalSignsSummary | null>(null);
  const [dataWarning, setDataWarning] = useState<string | null>(null);
  const [pendingConsent, setPendingConsent] = useState<any[]>([]);
  const [hrTrendData, setHrTrendData] = useState<
    Array<{ day: string; avgHR: number; minHR: number; maxHR: number }>
  >([]);
  const [healthScoreData, setHealthScoreData] = useState<
    Array<{ range: string; count: number }>
  >([]);
  const [unreadMessageCount, setUnreadMessageCount] = useState(0);

  useEffect(() => {
    loadDashboardData();
    // Set up polling for unread messages every 5 seconds
    const interval = setInterval(loadUnreadMessages, 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadUnreadMessages = async () => {
    try {
      const inbox = await api.getMessagingInbox();
      const totalUnread = inbox.reduce((sum, conv) => sum + conv.unread_count, 0);
      setUnreadMessageCount(totalUnread);
    } catch (e) {
      console.warn('Could not load unread messages:', e);
    }
  };

  const loadDashboardData = async () => {
    setLoading(true);
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

      // Redirect admin to admin page
      const role = (user as any).role || (user as any).user_role;
      if (role === 'admin') {
        navigate('/admin');
        return;
      }

      const [usersResult, statsResult, alertsResult, vitalsResult] =
        await withTimeout(
          Promise.allSettled([
            api.getAllUsers(1, 200),
            api.getAlertStats(),
            api.getAlerts(1, 5),
            api.getVitalSignsSummary(),
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

        // Load unread messages for clinicians
        try {
          await loadUnreadMessages();
        } catch (e) {
          console.warn('Could not load unread messages:', e);
        }
      }

      const usersList = usersResult.status === 'fulfilled' ? usersResult.value : null;
      const statsResponse = statsResult.status === 'fulfilled' ? statsResult.value : null;
      const alertsResponse = alertsResult.status === 'fulfilled' ? alertsResult.value : null;
      const vitalsSummaryResponse = vitalsResult.status === 'fulfilled' ? vitalsResult.value : null;

      const failedWidgets: string[] = [];
      if (usersResult.status === 'rejected') failedWidgets.push('patients');
      if (statsResult.status === 'rejected') failedWidgets.push('alert stats');
      if (alertsResult.status === 'rejected') failedWidgets.push('alerts');
      if (vitalsResult.status === 'rejected') failedWidgets.push('vitals summary');
      if (failedWidgets.length > 0) {
        setDataWarning(`Some dashboard widgets could not load: ${failedWidgets.join(', ')}.`);
      }

      console.log('Dashboard data loaded:', {
        user,
        usersCount: usersList?.total ?? 0,
        usersArray: usersList?.users?.length ?? 0,
        statsResponse,
        alertsResponse,
        vitalsSummary: vitalsSummaryResponse,
      });

      setCurrentUser(user);
      setAlertStats(
        statsResponse ?? {
          total: 0,
          by_severity: {},
          by_type: {},
          unacknowledged_count: 0,
        }
      );
      setRecentAlerts(alertsResponse?.alerts ?? []);
      setVitalsSummary(vitalsSummaryResponse ?? null);

      const activeCount = usersList?.users?.filter((u) => u.is_active).length ?? 0;
      const criticalCount = statsResponse?.by_severity?.critical ?? 0;
      const avgHeartRate = Number.isFinite(vitalsSummaryResponse?.avg_heart_rate)
        ? Math.round(vitalsSummaryResponse?.avg_heart_rate ?? 72)
        : 72;

      setStats({
        totalPatients: usersList?.total ?? 0,
        activeMonitoring: activeCount,
        criticalAlerts: criticalCount,
        avgHeartRate,
      });

      const patientUsers = (usersList?.users ?? []).filter((userItem) => {
        const userRole = ((userItem as any).user_role ?? (userItem as any).role ?? '').toLowerCase();
        return userRole === 'patient';
      });

      if (patientUsers.length > 0) {
        const historyResults = await Promise.allSettled(
          patientUsers.map((patient) => api.getVitalSignsHistoryForUser(patient.user_id, 7, 1, 100))
        );

        const groupedVitals: Record<string, number[]> = {};
        for (const result of historyResults) {
          if (result.status !== 'fulfilled') continue;
          const rows = result.value?.vitals ?? [];
          for (const row of rows) {
            const label = toWeekdayLabel(row?.timestamp);
            if (!label || typeof row?.heart_rate !== 'number') continue;
            if (!groupedVitals[label]) groupedVitals[label] = [];
            groupedVitals[label].push(row.heart_rate);
          }
        }

        const realTrendData = WEEKDAY_ORDER
          .filter((day) => (groupedVitals[day]?.length ?? 0) > 0)
          .map((day) => {
            const values = groupedVitals[day];
            const sum = values.reduce((total, value) => total + value, 0);
            return {
              day,
              avgHR: Math.round(sum / values.length),
              minHR: Math.min(...values),
              maxHR: Math.max(...values),
            };
          });

        setHrTrendData(realTrendData);

        const riskResults = await Promise.allSettled(
          patientUsers.map((patient) => api.getLatestRiskAssessmentForUser(patient.user_id))
        );

        const riskCounts = {
          low: 0,
          moderate: 0,
          high: 0,
          critical: 0,
        };

        for (const result of riskResults) {
          if (result.status !== 'fulfilled') continue;
          const level = (result.value?.risk_level ?? '').toLowerCase();
          if (level === 'low') riskCounts.low += 1;
          else if (level === 'moderate') riskCounts.moderate += 1;
          else if (level === 'high') riskCounts.high += 1;
          else if (level === 'critical') riskCounts.critical += 1;
        }

        setHealthScoreData([
          { range: 'Low Risk', count: riskCounts.low },
          { range: 'Moderate', count: riskCounts.moderate },
          { range: 'High Risk', count: riskCounts.high },
          { range: 'Critical', count: riskCounts.critical },
        ]);
      } else {
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

  const formatTimeAgo = (isoDate?: string) => {
    if (!isoDate) return 'Just now';
    const date = new Date(isoDate);
    const diffMs = Date.now() - date.getTime();
    const diffMin = Math.max(1, Math.floor(diffMs / 60000));
    if (diffMin < 60) return `${diffMin} min ago`;
    const diffHr = Math.floor(diffMin / 60);
    return `${diffHr} hr${diffHr > 1 ? 's' : ''} ago`;
  };

  const handleLogout = () => {
    api.logout();
    navigate('/login');
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
          onClick={loadDashboardData}
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
      {/* Header */}
      <header
        style={{
          backgroundColor: colors.neutral.white,
          borderBottom: `1px solid ${colors.neutral['300']}`,
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 32px',
            maxWidth: '1440px',
            margin: '0 auto',
          }}
        >
          {/* Logo/Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Heart size={28} color={colors.primary.default} fill={colors.primary.default} />
            <h1
              style={{
                margin: 0,
                fontSize: '20px',
                fontWeight: 700,
                color: colors.neutral['900'],
              }}
            >
              Adaptiv Health
            </h1>
          </div>

          {/* User Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <span style={{ ...typography.body, color: colors.neutral['700'] }}>
              {currentUser?.full_name || 'Clinician'}
            </span>
            <button
              onClick={() => navigate('/messages')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '6px',
                border: `1px solid ${colors.neutral['300']}`,
                backgroundColor: colors.neutral.white,
                cursor: 'pointer',
                color: unreadMessageCount > 0 ? colors.critical.badge : colors.neutral['700'],
                fontWeight: unreadMessageCount > 0 ? 600 : 500,
                transition: 'all 0.2s',
                position: 'relative',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = colors.neutral['100'];
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = colors.neutral.white;
              }}
            >
              <MessageSquare size={18} />
              Messages
              {unreadMessageCount > 0 && (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minWidth: '20px',
                    height: '20px',
                    backgroundColor: colors.critical.badge,
                    color: colors.neutral.white,
                    borderRadius: '50%',
                    fontSize: '12px',
                    fontWeight: 700,
                    marginLeft: '4px',
                  }}
                >
                  {unreadMessageCount}
                </span>
              )}
            </button>
            <button
              onClick={handleLogout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '6px',
                border: `1px solid ${colors.neutral['300']}`,
                backgroundColor: colors.neutral.white,
                cursor: 'pointer',
                color: colors.neutral['700'],
                fontWeight: 500,
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = colors.neutral['100'];
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = colors.neutral.white;
              }}
            >
              <LogOut size={18} />
              Logout
            </button>
          </div>
        </div>
      </header>

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
          <h3 style={typography.sectionTitle}>Vitals Summary</h3>
          <p style={{ ...typography.caption, marginBottom: '16px' }}>Last 7 days (aggregate)</p>
          {(vitalsSummary?.total_readings ?? 0) > 0 ? (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                gap: '12px',
              }}
            >
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
                <div style={typography.caption}>Avg HR</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {vitalsSummary?.avg_heart_rate ? Math.round(vitalsSummary.avg_heart_rate) : '--'} BPM
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
                <div style={typography.caption}>Min / Max HR</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {vitalsSummary?.min_heart_rate ? Math.round(vitalsSummary.min_heart_rate) : '--'} /{' '}
                  {vitalsSummary?.max_heart_rate ? Math.round(vitalsSummary.max_heart_rate) : '--'}
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
                <div style={typography.caption}>Avg SpO2</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {vitalsSummary?.avg_spo2 ? Math.round(vitalsSummary.avg_spo2) : '--'}%
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
                <div style={typography.caption}>Readings</div>
                <div style={{ ...typography.cardTitle, marginTop: '4px' }}>
                  {vitalsSummary?.total_readings ?? 0}
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
            <h3 style={typography.sectionTitle}>Avg HR Trend</h3>
            <p style={{ ...typography.caption, marginBottom: '16px' }}>Last 7 days</p>
            {hrTrendData.length === 0 ? (
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
                    domain={[40, 120]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: colors.neutral.white,
                      border: `1px solid ${colors.neutral['300']}`,
                      borderRadius: '6px',
                    }}
                  />
                  <Legend wrapperStyle={{ paddingTop: '12px' }} />
                  <Line
                    type="monotone"
                    dataKey="avgHR"
                    stroke={colors.critical.badge}
                    name="Avg HR (BPM)"
                    strokeWidth={2}
                    dot={{ fill: colors.critical.badge, r: 4 }}
                  />
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
            <p style={{ ...typography.caption, marginBottom: '16px' }}>Population snapshot</p>
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
              border: `1px solid #FF9800`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
              marginBottom: '32px',
            }}
          >
            <h3 style={{ ...typography.sectionTitle, color: '#E65100' }}>
              Pending Consent Requests ({pendingConsent.length})
            </h3>
            <p style={{ ...typography.caption, marginBottom: '16px' }}>
              These patients have requested to disable data sharing. Review each request.
            </p>
            {pendingConsent.map((req: any) => (
              <div
                key={req.user_id}
                style={{
                  padding: '12px 16px', borderRadius: '8px', backgroundColor: '#FFF3E0',
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
                      backgroundColor: '#4CAF50', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: '12px',
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
                      backgroundColor: '#f44336', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: '12px',
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
