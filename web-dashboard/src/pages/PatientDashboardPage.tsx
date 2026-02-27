/*
Patient dashboard page.

Personal view showing the patient's own:
- Latest vital signs
- Risk assessment
- Health recommendations
- Activity history
*/

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Heart,
  Activity,
  AlertTriangle,
  LogOut,
  TrendingUp,
  Zap,
} from 'lucide-react';
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
import { User, AlertResponse } from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';

interface PatientStats {
  latestHeartRate: number;
  latestSpO2: number;
  latestBP: string;
  riskLevel: string;
  riskScore: number;
  avgHeartRate: number;
}

const PatientDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<PatientStats>({
    latestHeartRate: 0,
    latestSpO2: 0,
    latestBP: '--',
    riskLevel: 'low',
    riskScore: 0,
    avgHeartRate: 72,
  });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [vitalHistory, setVitalHistory] = useState<any[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<AlertResponse[]>([]);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    try {
      // Get current user info
      const user = await api.getCurrentUser();
      setCurrentUser(user);

      // Get latest vitals
      try {
        const vitals = await api.getLatestVitalSigns();
        if (vitals) {
          const bp = vitals.blood_pressure;
          const bpStr = bp ? `${bp.systolic}/${bp.diastolic}` : '--/--';
          setStats((prev) => ({
            ...prev,
            latestHeartRate: vitals.heart_rate || 0,
            latestSpO2: vitals.spo2 || 0,
            latestBP: bpStr,
          }));
        }
      } catch (e: any) {
        // 404 is expected for new patients with no vitals yet
        if (e.response?.status !== 404) {
          console.error('Error loading vitals:', e);
        }
      }

      // Get risk assessment
      try {
        const risk = await api.getLatestRiskAssessment();
        if (risk) {
          setStats((prev) => ({
            ...prev,
            riskLevel: risk.risk_level || 'low',
            riskScore: risk.risk_score || 0,
          }));
        }
      } catch (e: any) {
        // 404 is expected for new patients with no risk assessments yet
        if (e.response?.status !== 404) {
          console.error('Error loading risk:', e);
        }
      }

      // Get vital history for chart
      try {
        const historyResponse = await api.getVitalSignsHistory(1, 50);
        if (historyResponse && historyResponse.vitals && historyResponse.vitals.length > 0) {
          const chartData = historyResponse.vitals.map((v: any) => ({
            ...v,
            heart_rate: v.heart_rate,
          }));
          setVitalHistory(chartData);
          const avgHR =
            Math.round(
              historyResponse.vitals.reduce((sum: number, v: any) => sum + (v.heart_rate || 0), 0) /
                historyResponse.vitals.length
            ) || 72;
          setStats((prev) => ({
            ...prev,
            avgHeartRate: avgHR,
          }));
        }
      } catch (e: any) {
        // 404 is expected for new patients
        if (e.response?.status !== 404) {
          console.error('Error loading history:', e);
        }
      }

      // Get recent alerts
      try {
        const alerts = await api.getAlerts(1, 10);
        if (alerts && alerts.alerts && alerts.alerts.length > 0) {
          setRecentAlerts(alerts.alerts.slice(0, 5));
        }
      } catch (e: any) {
        // Silently ignore alert loading errors - they're not critical
        if (e.response?.status !== 404) {
          console.error('Error loading alerts:', e);
        }
      }

      setLoading(false);
    } catch (error) {
      console.error('Error loading patient dashboard:', error);
      setLoadError('Failed to load dashboard data');
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
      localStorage.removeItem('token');
      navigate('/login');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: '20px', fontSize: '18px', color: colors.neutral['500'] }}>
            Loading your health dashboard...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.neutral['50'] }}>
      {/* Header */}
      <header
        style={{
          backgroundColor: colors.neutral.white,
          borderBottom: `1px solid ${colors.neutral['300']}`,
          padding: '16px 32px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <h1 style={{ ...typography.pageTitle, margin: 0 }}>My Health</h1>
          <p style={{ ...typography.caption, color: colors.neutral['500'], margin: '4px 0 0 0' }}>
            Welcome, {currentUser?.full_name || 'Patient'}
          </p>
        </div>
        <button
          onClick={handleLogout}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            backgroundColor: colors.critical.background,
            border: `1px solid ${colors.critical.border}`,
            borderRadius: '6px',
            cursor: 'pointer',
            color: colors.critical.badge,
            fontWeight: 500,
          }}
        >
          <LogOut size={18} />
          Sign Out
        </button>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: '1440px', margin: '0 auto', padding: '32px' }}>
        {loadError && (
          <div
            style={{
              backgroundColor: colors.critical.background,
              border: `1px solid ${colors.critical.border}`,
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '24px',
              color: colors.critical.text,
            }}
          >
            {loadError}
          </div>
        )}

        {/* Stats Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '24px',
            marginBottom: '32px',
          }}
        >
          {/* Heart Rate Card */}
          <div
            style={{
              backgroundColor: colors.critical.background,
              border: `1px solid ${colors.critical.border}`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <Heart size={24} color={colors.critical.badge} />
              <div style={{ ...typography.body, fontWeight: 600, color: colors.critical.text }}>
                Heart Rate
              </div>
            </div>
            <div style={{ fontSize: '36px', fontWeight: 700, marginBottom: '4px' }}>
              {stats.latestHeartRate}
            </div>
            <div style={{ ...typography.caption, color: colors.neutral['500'] }}>BPM</div>
          </div>

          {/* Oxygen Level Card */}
          <div
            style={{
              backgroundColor: colors.stable.background,
              border: `1px solid ${colors.stable.border}`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <Zap size={24} color={colors.stable.badge} />
              <div style={{ ...typography.body, fontWeight: 600, color: colors.stable.text }}>
                Oxygen Level
              </div>
            </div>
            <div style={{ fontSize: '36px', fontWeight: 700, marginBottom: '4px' }}>
              {stats.latestSpO2}
            </div>
            <div style={{ ...typography.caption, color: colors.neutral['500'] }}>%</div>
          </div>

          {/* Blood Pressure Card */}
          <div
            style={{
              backgroundColor: colors.primary.light,
              border: `1px solid ${colors.primary.default}30`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <Activity size={24} color={colors.primary.default} />
              <div style={{ ...typography.body, fontWeight: 600, color: colors.primary.default }}>
                Blood Pressure
              </div>
            </div>
            <div style={{ fontSize: '36px', fontWeight: 700, marginBottom: '4px' }}>
              {stats.latestBP}
            </div>
            <div style={{ ...typography.caption, color: colors.neutral['500'] }}>mmHg</div>
          </div>

          {/* Risk Level Card */}
          <div
            style={{
              backgroundColor: colors.warning.background,
              border: `1px solid ${colors.warning.border}`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <AlertTriangle size={24} color={colors.warning.badge} />
              <div style={{ ...typography.body, fontWeight: 600, color: colors.warning.text }}>
                Risk Level
              </div>
            </div>
            <div style={{ fontSize: '36px', fontWeight: 700, marginBottom: '4px' }}>
              {stats.riskLevel.charAt(0).toUpperCase() + stats.riskLevel.slice(1)}
            </div>
            <div style={{ ...typography.caption, color: colors.neutral['500'] }}>
              ({(stats.riskScore * 100).toFixed(0)}%)
            </div>
          </div>
        </div>

        {/* Charts Section */}
        <div style={{ marginBottom: '32px' }}>
          <div
            style={{
              backgroundColor: colors.neutral.white,
              border: `1px solid ${colors.neutral['300']}`,
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <h2 style={{ ...typography.sectionTitle, marginTop: 0, marginBottom: '24px' }}>
              <TrendingUp size={20} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
              7-Day Heart Rate Trend
            </h2>
            {vitalHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={vitalHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="timestamp"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => {
                      try {
                        return new Date(value).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                        });
                      } catch {
                        return value;
                      }
                    }}
                  />
                  <YAxis />
                  <Tooltip
                    labelFormatter={(value) => {
                      try {
                        return new Date(value).toLocaleDateString();
                      } catch {
                        return value;
                      }
                    }}
                    formatter={(value) => [`${value} BPM`, 'Heart Rate']}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="heart_rate"
                    stroke={colors.critical.badge}
                    strokeWidth={2}
                    name="Heart Rate (BPM)"
                    dot={false}
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
                  color: colors.neutral['500'],
                }}
              >
                No vital data available yet
              </div>
            )}
          </div>
        </div>

        {/* Recent Alerts */}
        {recentAlerts.length > 0 && (
          <div>
            <div
              style={{
                backgroundColor: colors.neutral.white,
                border: `1px solid ${colors.neutral['300']}`,
                borderRadius: '12px',
                padding: '24px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
              }}
            >
              <h2 style={{ ...typography.sectionTitle, marginTop: 0, marginBottom: '16px' }}>
                <AlertTriangle size={20} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
                Recent Alerts
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {recentAlerts.map((alert, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '8px',
                      backgroundColor:
                        alert.severity === 'critical'
                          ? colors.critical.background
                          : colors.warning.background,
                      borderLeft: `4px solid ${
                        alert.severity === 'critical'
                          ? colors.critical.badge
                          : colors.warning.badge
                      }`,
                    }}
                  >
                    <div style={{ ...typography.body, fontWeight: 600 }}>{alert.title}</div>
                    <div
                      style={{
                        ...typography.caption,
                        color: colors.neutral['600'],
                        marginTop: '4px',
                      }}
                    >
                      {alert.message}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default PatientDashboardPage;
