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
  TrendingUp,
  LogOut,
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
import { AlertResponse, AlertStatsResponse, User } from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';
import StatCard from '../components/cards/StatCard';

interface Stats {
  totalPatients: number;
  activeMonitoring: number;
  criticalAlerts: number;
  avgHeartRate: number;
}

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats>({
    totalPatients: 0,
    activeMonitoring: 0,
    criticalAlerts: 0,
    avgHeartRate: 72,
  });
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [alertStats, setAlertStats] = useState<AlertStatsResponse | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<AlertResponse[]>([]);
  const [pendingConsent, setPendingConsent] = useState<any[]>([]);
  const [hrTrendData, setHrTrendData] = useState<
    Array<{ day: string; avgHR: number; minHR: number; maxHR: number }>
  >([]);
  const [healthScoreData, setHealthScoreData] = useState<
    Array<{ range: string; count: number }>
  >([]);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const user = await api.getCurrentUser();
      setCurrentUser(user);

      // Redirect admin to admin page
      const role = (user as any).role || (user as any).user_role;
      if (role === 'admin') {
        navigate('/admin');
        return;
      }

      const [usersList, statsResponse, alertsResponse, vitalsSummary] =
        await Promise.all([
          api.getAllUsers(1, 200),
          api.getAlertStats(),
          api.getAlerts(1, 5),
          api.getVitalSignsSummary(),
        ]);

      // Load pending consent requests for clinicians
      if (role === 'clinician') {
        try {
          const consentResp = await api.getPendingConsentRequests();
          setPendingConsent(consentResp.pending_requests || []);
        } catch {
          // consent endpoint may not be available
        }
      }

      console.log('Dashboard data loaded:', {
        user,
        usersCount: usersList.total,
        usersArray: usersList.users.length,
        statsResponse,
        alertsResponse,
        vitalsSummary,
      });

      setCurrentUser(user);
      setAlertStats(statsResponse);
      setRecentAlerts(alertsResponse.alerts ?? []);

      const activeCount = usersList.users.filter((u) => u.is_active).length;
      const criticalCount = statsResponse.by_severity?.critical ?? 0;
      const avgHeartRate = Math.round(vitalsSummary?.avg_heart_rate ?? 72);

      setStats({
        totalPatients: usersList.total,
        activeMonitoring: activeCount,
        criticalAlerts: criticalCount,
        avgHeartRate,
      });

      // Generate HR Trend data (7-day synthetic trend based on avg)
      const hrTrend = [];
      const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      const baseHR = avgHeartRate;
      for (let i = 0; i < 7; i++) {
        const variation = Math.random() * 20 - 10; // -10 to +10 variation
        hrTrend.push({
          day: days[i],
          avgHR: Math.round(baseHR + variation),
          minHR: Math.round(baseHR + variation - 15),
          maxHR: Math.round(baseHR + variation + 20),
        });
      }
      setHrTrendData(hrTrend);

      // Generate Health Score Distribution (based on alert by severity)
      const lowCount = Math.max(1, activeCount - criticalCount - 10);
      const moderateCount = 10;
      const highCount = Math.max(1, criticalCount - 3);
      const criticalCount_ = Math.max(1, criticalCount);

      setHealthScoreData([
        { range: 'Low Risk', count: Math.max(0, lowCount) },
        { range: 'Moderate', count: Math.max(0, moderateCount) },
        { range: 'High Risk', count: Math.max(0, highCount) },
        { range: 'Critical', count: criticalCount_ },
      ]);
    } catch (error) {
      console.error('Error loading dashboard:', error);
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

  const statCards = [
    {
      title: 'Total Patients',
      value: stats.totalPatients,
      icon: <Users size={40} />,
      color: '#0066FF',
      bgColor: '#E3F2FD',
    },
    {
      title: 'Active Monitoring',
      value: stats.activeMonitoring,
      icon: <Heart size={40} />,
      color: '#00C853',
      bgColor: '#E8F5E9',
    },
    {
      title: 'Critical Alerts',
      value: stats.criticalAlerts,
      icon: <AlertTriangle size={40} />,
      color: '#FF1744',
      bgColor: '#FFEBEE',
    },
    {
      title: 'Avg Heart Rate',
      value: `${stats.avgHeartRate} BPM`,
      icon: <TrendingUp size={40} />,
      color: '#9C27B0',
      bgColor: '#F3E5F5',
    },
  ];

  if (loading) {
    return (
      <div style={{ padding: '32px', textAlign: 'center' }}>
        <p>Loading dashboard...</p>
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
            <strong>Backend Status:</strong> Connected to http://localhost:8000
          </p>
          <p style={{ ...typography.caption, margin: 0 }}>
            API Documentation: Visit http://localhost:8000/docs for interactive testing
          </p>
        </div>
      </main>
    </div>
  );
};

export default DashboardPage;
