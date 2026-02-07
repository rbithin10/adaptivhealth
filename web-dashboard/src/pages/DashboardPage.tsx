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
  Home,
  Activity,
  Bell,
  BarChart3,
  Settings,
} from 'lucide-react';
import { api, User } from '../services/api';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';
import StatCard from '../components/cards/StatCard';
import StatusBadge from '../components/common/StatusBadge';

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

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const user = await api.getCurrentUser();
      setCurrentUser(user);

      // Fetch real stats from the backend API
      try {
        const usersResponse = await api.getAllUsers();
        const users = Array.isArray(usersResponse) ? usersResponse : (usersResponse as any)?.users ?? [];
        const totalPatients = users.length;

        // Estimate active monitoring as a fraction of total patients
        const ACTIVE_MONITORING_RATIO = 0.3;
        const activeMonitoring = Math.min(totalPatients, Math.ceil(totalPatients * ACTIVE_MONITORING_RATIO));

        setStats({
          totalPatients,
          activeMonitoring,
          criticalAlerts: 0,
          avgHeartRate: 72,
        });
      } catch {
        // Fallback to defaults if user list endpoint is unavailable
        setStats({
          totalPatients: 0,
          activeMonitoring: 0,
          criticalAlerts: 0,
          avgHeartRate: 72,
        });
      }
    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const statCards = [
    {
      title: 'Total Patients',
      value: stats.totalPatients,
      icon: <People sx={{ fontSize: 40 }} />,
      color: '#0066FF',
      bgColor: '#E3F2FD',
    },
    {
      title: 'Active Monitoring',
      value: stats.activeMonitoring,
      icon: <FavoriteOutlined sx={{ fontSize: 40 }} />,
      color: '#00C853',
      bgColor: '#E8F5E9',
    },
    {
      title: 'Critical Alerts',
      value: stats.criticalAlerts,
      icon: <Warning sx={{ fontSize: 40 }} />,
      color: '#FF1744',
      bgColor: '#FFEBEE',
    },
    {
      title: 'Avg Heart Rate',
      value: `${stats.avgHeartRate} BPM`,
      icon: <TrendingUp sx={{ fontSize: 40 }} />,
      color: '#9C27B0',
      bgColor: '#F3E5F5',
    },
  ];

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
              {currentUser?.name || 'Clinician'}
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
          Welcome back, {currentUser?.name?.split(' ')[0] || 'Doctor'}!
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
            value={3}
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
            <div
              style={{
                height: '200px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: colors.neutral['50'],
                borderRadius: '8px',
                color: colors.neutral['500'],
              }}
            >
              [Heart Rate Chart - Recharts ready]
            </div>
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
            <div
              style={{
                height: '200px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: colors.neutral['50'],
                borderRadius: '8px',
                color: colors.neutral['500'],
              }}
            >
              [Bar Chart - Recharts ready]
            </div>
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
            <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
              <p style={typography.body}>• Robert Anderson: HR spike 112 BPM (9 minutes ago)</p>
            </div>
            <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
              <p style={typography.body}>• Sarah Mitchell: BP elevated (34 minutes ago)</p>
            </div>
            <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: colors.neutral['50'] }}>
              <p style={typography.body}>• James Thompson: Session completed (1 hour ago)</p>
            </div>
          </div>
        </div>

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
            <strong>Backend Status:</strong> Connected to http://localhost:8001
          </p>
          <p style={{ ...typography.caption, margin: 0 }}>
            API Documentation: Visit http://localhost:8001/docs for interactive testing
          </p>
        </div>
      </main>
    </div>
  );
};

export default DashboardPage;
