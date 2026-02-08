/*
Admin page.

User management for admin role. Allows:
- Creating patients and clinicians
- Setting temporary passwords
- Deactivating users

Does NOT show any PHI (vitals, risk, recommendations, alerts details).
*/

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  LogOut,
  Heart,
  UserPlus,
  Key,
  XCircle,
} from 'lucide-react';
import { api } from '../services/api';
import { User } from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';

const AdminPage: React.FC = () => {
  const navigate = useNavigate();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  // Create user form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('patient');
  const [createMessage, setCreateMessage] = useState('');

  // Reset password form
  const [resetUserId, setResetUserId] = useState<number | null>(null);
  const [resetPassword, setResetPassword] = useState('');
  const [resetMessage, setResetMessage] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [user, usersList] = await Promise.all([
        api.getCurrentUser(),
        api.getAllUsers(1, 200),
      ]);
      setCurrentUser(user);

      // Check admin role
      const role = (user as any).role || (user as any).user_role;
      if (role !== 'admin') {
        navigate('/dashboard');
        return;
      }

      setUsers(usersList.users);
    } catch (error) {
      console.error('Error loading admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    api.logout();
    navigate('/login');
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateMessage('');
    try {
      await api.createUser({
        email: newEmail,
        password: newPassword,
        name: newName,
        role: newRole,
      });
      setCreateMessage('User created successfully');
      setNewEmail('');
      setNewName('');
      setNewPassword('');
      setShowCreateForm(false);
      loadData();
    } catch (err: any) {
      setCreateMessage(err.response?.data?.error?.message || err.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetMessage('');
    if (!resetUserId) return;
    try {
      await api.adminResetUserPassword(resetUserId, resetPassword);
      setResetMessage('Password reset successfully');
      setResetUserId(null);
      setResetPassword('');
    } catch (err: any) {
      setResetMessage(err.response?.data?.error?.message || err.response?.data?.detail || 'Failed to reset password');
    }
  };

  const handleDeactivate = async (userId: number) => {
    if (!window.confirm('Are you sure you want to deactivate this user?')) return;
    try {
      await api.deactivateUser(userId);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to deactivate user');
    }
  };

  if (loading) {
    return <div style={{ padding: '32px', textAlign: 'center' }}>Loading...</div>;
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.neutral['50'] }}>
      {/* Header */}
      <header style={{
        backgroundColor: colors.neutral.white,
        borderBottom: `1px solid ${colors.neutral['300']}`,
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 32px', maxWidth: '1440px', margin: '0 auto',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Heart size={28} color={colors.primary.default} fill={colors.primary.default} />
            <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>Adaptiv Health — Admin</h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <span style={{ ...typography.body, color: colors.neutral['700'] }}>
              {currentUser?.full_name || 'Admin'}
            </span>
            <button onClick={handleLogout} style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '8px 16px', borderRadius: '6px',
              border: `1px solid ${colors.neutral['300']}`, backgroundColor: colors.neutral.white,
              cursor: 'pointer', fontWeight: 500,
            }}>
              <LogOut size={18} /> Logout
            </button>
          </div>
        </div>
      </header>

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px' }}>
        <h2 style={typography.pageTitle}>User Management</h2>
        <p style={{ ...typography.body, color: colors.neutral['500'], marginBottom: '24px' }}>
          Create and manage user accounts. Admin users cannot view patient health data (PHI).
        </p>

        {/* Messages */}
        {createMessage && (
          <div style={{
            padding: '12px 16px', marginBottom: '16px', borderRadius: '8px',
            backgroundColor: createMessage.includes('success') ? '#E8F5E9' : '#FFEBEE',
            color: createMessage.includes('success') ? '#2E7D32' : '#C62828',
          }}>
            {createMessage}
          </div>
        )}
        {resetMessage && (
          <div style={{
            padding: '12px 16px', marginBottom: '16px', borderRadius: '8px',
            backgroundColor: resetMessage.includes('success') ? '#E8F5E9' : '#FFEBEE',
            color: resetMessage.includes('success') ? '#2E7D32' : '#C62828',
          }}>
            {resetMessage}
          </div>
        )}

        {/* Create User Button */}
        <div style={{ marginBottom: '24px' }}>
          <button onClick={() => setShowCreateForm(!showCreateForm)} style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 20px', borderRadius: '8px', border: 'none',
            backgroundColor: colors.primary.default, color: '#fff',
            cursor: 'pointer', fontWeight: 600, fontSize: '14px',
          }}>
            <UserPlus size={18} /> Create New User
          </button>
        </div>

        {/* Create User Form */}
        {showCreateForm && (
          <div style={{
            backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px', padding: '24px', marginBottom: '24px',
          }}>
            <h3 style={typography.sectionTitle}>Create New User</h3>
            <form onSubmit={handleCreateUser} style={{ display: 'grid', gap: '12px', maxWidth: '500px', marginTop: '16px' }}>
              <input type="email" placeholder="Email" value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)} required
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }} />
              <input type="text" placeholder="Full Name" value={newName}
                onChange={(e) => setNewName(e.target.value)} required
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }} />
              <input type="password" placeholder="Temporary Password (min 8 chars)" value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)} required minLength={8}
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }} />
              <select value={newRole} onChange={(e) => setNewRole(e.target.value)}
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }}>
                <option value="patient">Patient</option>
                <option value="clinician">Clinician</option>
              </select>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="submit" style={{
                  padding: '10px 20px', borderRadius: '6px', border: 'none',
                  backgroundColor: colors.primary.default, color: '#fff', cursor: 'pointer', fontWeight: 600,
                }}>Create</button>
                <button type="button" onClick={() => setShowCreateForm(false)} style={{
                  padding: '10px 20px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`,
                  backgroundColor: '#fff', cursor: 'pointer',
                }}>Cancel</button>
              </div>
            </form>
          </div>
        )}

        {/* Reset Password Modal */}
        {resetUserId && (
          <div style={{
            backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px', padding: '24px', marginBottom: '24px',
          }}>
            <h3 style={typography.sectionTitle}>Reset Password for User #{resetUserId}</h3>
            <form onSubmit={handleResetPassword} style={{ display: 'flex', gap: '12px', maxWidth: '500px', marginTop: '12px' }}>
              <input type="password" placeholder="New temporary password" value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)} required minLength={8}
                style={{ flex: 1, padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }} />
              <button type="submit" style={{
                padding: '10px 20px', borderRadius: '6px', border: 'none',
                backgroundColor: '#FF9800', color: '#fff', cursor: 'pointer', fontWeight: 600,
              }}>Reset</button>
              <button type="button" onClick={() => { setResetUserId(null); setResetPassword(''); }} style={{
                padding: '10px 20px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`,
                backgroundColor: '#fff', cursor: 'pointer',
              }}>Cancel</button>
            </form>
          </div>
        )}

        {/* User Table */}
        <div style={{
          backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`,
          borderRadius: '12px', overflow: 'hidden',
        }}>
          <div style={{
            display: 'grid', gridTemplateColumns: '60px 200px 100px 100px 100px 200px',
            gap: '16px', padding: '16px 24px', backgroundColor: colors.neutral['50'],
            borderBottom: `1px solid ${colors.neutral['300']}`,
            fontWeight: 600, fontSize: '12px', textTransform: 'uppercase' as const, color: colors.neutral['700'],
          }}>
            <div>ID</div><div>Name / Email</div><div>Role</div><div>Status</div><div>Active</div><div>Actions</div>
          </div>

          {users.map((u, idx) => (
            <div key={u.user_id} style={{
              display: 'grid', gridTemplateColumns: '60px 200px 100px 100px 100px 200px',
              gap: '16px', padding: '12px 24px', alignItems: 'center',
              borderBottom: idx < users.length - 1 ? `1px solid ${colors.neutral['300']}` : 'none',
              backgroundColor: idx % 2 === 0 ? '#fff' : colors.neutral['50'],
            }}>
              <div style={typography.body}>{u.user_id}</div>
              <div>
                <div style={{ ...typography.body, fontWeight: 600 }}>{u.full_name || '—'}</div>
                <div style={{ ...typography.caption, color: colors.neutral['500'] }}>{u.email}</div>
              </div>
              <div style={{
                display: 'inline-block', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 600,
                backgroundColor: (u as any).role === 'admin' ? '#E3F2FD' : (u as any).role === 'clinician' ? '#E8F5E9' : '#FFF3E0',
                color: (u as any).role === 'admin' ? '#1565C0' : (u as any).role === 'clinician' ? '#2E7D32' : '#E65100',
              }}>
                {(u as any).role || (u as any).user_role}
              </div>
              <div style={typography.body}>{u.is_verified ? '✓ Verified' : 'Pending'}</div>
              <div style={typography.body}>{u.is_active ? '✓ Active' : '✗ Inactive'}</div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button onClick={() => { setResetUserId(u.user_id); setResetMessage(''); }} title="Reset Password" style={{
                  padding: '4px 8px', borderRadius: '4px', border: 'none',
                  backgroundColor: '#FFF3E0', color: '#E65100', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px',
                }}>
                  <Key size={14} /> Reset PW
                </button>
                {u.is_active && u.user_id !== currentUser?.user_id && (
                  <button onClick={() => handleDeactivate(u.user_id)} title="Deactivate" style={{
                    padding: '4px 8px', borderRadius: '4px', border: 'none',
                    backgroundColor: '#FFEBEE', color: '#C62828', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px',
                  }}>
                    <XCircle size={14} /> Deactivate
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        <p style={{ ...typography.caption, marginTop: '16px' }}>
          Showing {users.length} users. Admin users cannot view patient health data (PHI).
        </p>
      </main>
    </div>
  );
};

export default AdminPage;
