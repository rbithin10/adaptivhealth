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
  LogOut,
  Heart,
  UserPlus,
  Key,
  XCircle,
  Edit2,
} from 'lucide-react';
import { Snackbar, Alert as MuiAlert } from '@mui/material';
import { api } from '../services/api';
import { User } from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';

const AdminPage: React.FC = () => {
  const navigate = useNavigate();
  // Full list of users and loading state
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  // Fields for assigning a clinician to a patient
  const [clinicians, setClinicians] = useState<User[]>([]);
  const [assigningPatient, setAssigningPatient] = useState<number | null>(null);
  const [selectedClinician, setSelectedClinician] = useState<number | null>(null);
  const [assignMessage, setAssignMessage] = useState('');

  // Fields for the "Create New User" form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('patient');
  const [createMessage, setCreateMessage] = useState('');

  // Fields for the "Reset Password" form
  const [resetUserId, setResetUserId] = useState<number | null>(null);
  const [resetPassword, setResetPassword] = useState('');
  const [resetMessage, setResetMessage] = useState('');

  // Fields for the "Edit User" form
  const [editUserId, setEditUserId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editAge, setEditAge] = useState<number | undefined>(undefined);
  const [editGender, setEditGender] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editMessage, setEditMessage] = useState('');
  // Prevents double-clicks on submit buttons
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Toast notification state
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error'>('success');

  const showSnackbar = (message: string, severity: 'success' | 'error') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const getErrorMessage = (err: unknown, fallback: string): string => {
    if (
      typeof err === 'object' &&
      err !== null &&
      'response' in err &&
      typeof (err as { response?: { data?: { error?: { message?: string }; detail?: string } } }).response === 'object'
    ) {
      const responseData = (err as { response?: { data?: { error?: { message?: string }; detail?: string } } }).response?.data;
      return responseData?.error?.message || responseData?.detail || fallback;
    }
    return err instanceof Error ? err.message : fallback;
  };

  // Figure out what role a user has (handles different API field names)
  const getUserRole = (user: Partial<User> & { role?: string; user_role?: string }): string => {
    return ((user.user_role || user.role || '') as string).toLowerCase();
  };

  // Fetch user list and current admin profile when the page loads
  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load all users; redirect away if the current user isn't an admin
  const loadData = async () => {
    try {
      const [user, usersList] = await Promise.all([
        api.getCurrentUser(),
        api.getAllUsers(1, 200),
      ]);
      setCurrentUser(user);

      // Check admin role
      const role = getUserRole(user as User);
      if (role !== 'admin') {
        navigate('/dashboard');
        return;
      }

      setUsers(usersList.users);
      
      // Filter clinicians for assignment dropdown
      const clinicianList = usersList.users.filter((u) => getUserRole(u) === 'clinician');
      setClinicians(clinicianList);
    } catch (error) {
      console.error('Error loading admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Sign out and return to login
  const handleLogout = async () => {
    await api.logout();
    navigate('/login');
  };

  // Submit the "Create New User" form
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateMessage('');
    setIsSubmitting(true);
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
      await loadData();
    } catch (err: unknown) {
      setCreateMessage(getErrorMessage(err, 'Failed to create user'));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit the "Reset Password" form
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetMessage('');
    if (!resetUserId) return;
    setIsSubmitting(true);
    try {
      await api.adminResetUserPassword(resetUserId, resetPassword);
      setResetMessage('Password reset successfully');
      setResetUserId(null);
      setResetPassword('');
    } catch (err: unknown) {
      setResetMessage(getErrorMessage(err, 'Failed to reset password'));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Deactivate a user account (with confirmation prompt)
  const handleDeactivate = async (userId: number) => {
    if (!window.confirm('Are you sure you want to deactivate this user?')) return;
    setIsSubmitting(true);
    try {
      await api.deactivateUser(userId);
      await loadData();
    } catch (err: unknown) {
      showSnackbar(getErrorMessage(err, 'Failed to deactivate user'), 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Populate the edit form with a user's current details
  const handleEditUser = (user: User) => {
    setEditUserId(user.user_id);
    setEditName(user.full_name || '');
    setEditAge(user.age);
    setEditGender(user.gender || '');
    setEditPhone(user.phone || '');
    setEditMessage('');
  };

  // Save changes from the "Edit User" form
  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setEditMessage('');
    if (!editUserId) return;
    setIsSubmitting(true);
    try {
      await api.updateUser(editUserId, {
        name: editName,
        age: editAge,
        gender: editGender || undefined,
        phone: editPhone || undefined,
      });
      setEditMessage('User updated successfully');
      setEditUserId(null);
      loadData();
    } catch (err: unknown) {
      setEditMessage(getErrorMessage(err, 'Failed to update user'));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Assign a clinician to a patient so they show up in that clinician's list
  const handleAssignClinician = async (patientId: number, clinicianId: number) => {
    setAssignMessage('');
    setIsSubmitting(true);
    try {
      await api.assignClinicianToPatient(patientId, clinicianId);
      setAssignMessage(`Patient assigned to clinician successfully`);
      setAssigningPatient(null);
      setSelectedClinician(null);
      await loadData(); // Reload to show updated assignment
    } catch (err: unknown) {
      setAssignMessage(getErrorMessage(err, 'Failed to assign clinician'));
    } finally {
      setIsSubmitting(false);
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
        {editMessage && (
          <div style={{
            padding: '12px 16px', marginBottom: '16px', borderRadius: '8px',
            backgroundColor: editMessage.includes('success') ? '#E8F5E9' : '#FFEBEE',
            color: editMessage.includes('success') ? '#2E7D32' : '#C62828',
          }}>
            {editMessage}
          </div>
        )}
        {assignMessage && (
          <div style={{
            padding: '12px 16px', marginBottom: '16px', borderRadius: '8px',
            backgroundColor: assignMessage.includes('success') ? '#E8F5E9' : '#FFEBEE',
            color: assignMessage.includes('success') ? '#2E7D32' : '#C62828',
          }}>
            {assignMessage}
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
                onChange={(e) => setNewEmail(e.target.value)} required disabled={isSubmitting}
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }} />
              <input type="text" placeholder="Full Name" value={newName}
                onChange={(e) => setNewName(e.target.value)} required disabled={isSubmitting}
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }} />
              <input type="password" placeholder="Temporary Password (min 8 chars)" value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)} required minLength={8} disabled={isSubmitting}
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }} />
              <select value={newRole} onChange={(e) => setNewRole(e.target.value)} disabled={isSubmitting}
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }}>
                <option value="patient">Patient</option>
                <option value="clinician">Clinician</option>
              </select>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="submit" disabled={isSubmitting} style={{
                  padding: '10px 20px', borderRadius: '6px', border: 'none',
                  backgroundColor: isSubmitting ? colors.neutral['300'] : colors.primary.default, 
                  color: '#fff', cursor: isSubmitting ? 'not-allowed' : 'pointer', fontWeight: 600,
                }}>{isSubmitting ? 'Creating...' : 'Create'}</button>
                <button type="button" onClick={() => setShowCreateForm(false)} disabled={isSubmitting} style={{
                  padding: '10px 20px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`,
                  backgroundColor: '#fff', cursor: isSubmitting ? 'not-allowed' : 'pointer',
                }}>Cancel</button>
              </div>
            </form>
          </div>
        )}

        {/* Edit User Modal */}
        {editUserId && (
          <div style={{
            backgroundColor: colors.neutral.white, border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px', padding: '24px', marginBottom: '24px',
          }}>
            <h3 style={typography.sectionTitle}>Edit User #{editUserId}</h3>
            <form onSubmit={handleUpdateUser} style={{ display: 'grid', gap: '12px', maxWidth: '500px', marginTop: '16px' }}>
              <input
                type="text"
                placeholder="Full Name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                required
                disabled={isSubmitting}
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }}
              />
              <input
                type="number"
                placeholder="Age"
                value={editAge || ''}
                onChange={(e) => setEditAge(e.target.value ? parseInt(e.target.value) : undefined)}
                min={1}
                max={120}
                disabled={isSubmitting}
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }}
              />
              <select
                value={editGender}
                onChange={(e) => setEditGender(e.target.value)}
                disabled={isSubmitting}
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }}
              >
                <option value="">Select Gender</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
              <input
                type="tel"
                placeholder="Phone (optional)"
                value={editPhone}
                onChange={(e) => setEditPhone(e.target.value)}
                disabled={isSubmitting}
                style={{ padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{
                    padding: '10px 20px',
                    borderRadius: '6px',
                    border: 'none',
                    backgroundColor: isSubmitting ? colors.neutral['300'] : colors.primary.default,
                    color: '#fff',
                    cursor: isSubmitting ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                  }}
                >
                  {isSubmitting ? 'Updating...' : 'Update'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditUserId(null);
                    setEditMessage('');
                  }}
                  disabled={isSubmitting}
                  style={{
                    padding: '10px 20px',
                    borderRadius: '6px',
                    border: `1px solid ${colors.neutral['300']}`,
                    backgroundColor: '#fff',
                    cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  }}
                >
                  Cancel
                </button>
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
                onChange={(e) => setResetPassword(e.target.value)} required minLength={8} disabled={isSubmitting}
                style={{ flex: 1, padding: '10px 12px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '14px' }} />
              <button type="submit" disabled={isSubmitting} style={{
                padding: '10px 20px', borderRadius: '6px', border: 'none',
                backgroundColor: isSubmitting ? colors.neutral['300'] : '#FF9800', color: '#fff', cursor: isSubmitting ? 'not-allowed' : 'pointer', fontWeight: 600,
              }}>{isSubmitting ? 'Resetting...' : 'Reset'}</button>
              <button type="button" onClick={() => { setResetUserId(null); setResetPassword(''); }} disabled={isSubmitting} style={{
                padding: '10px 20px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`,
                backgroundColor: '#fff', cursor: isSubmitting ? 'not-allowed' : 'pointer',
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
            display: 'grid', gridTemplateColumns: '60px 200px 100px 100px 100px 180px 200px',
            gap: '16px', padding: '16px 24px', backgroundColor: colors.neutral['50'],
            borderBottom: `1px solid ${colors.neutral['300']}`,
            fontWeight: 600, fontSize: '12px', textTransform: 'uppercase' as const, color: colors.neutral['700'],
          }}>
            <div>ID</div><div>Name / Email</div><div>Role</div><div>Status</div><div>Active</div><div>Assign Clinician</div><div>Actions</div>
          </div>

          {users.map((u, idx) => {
            const userRole = getUserRole(u);
            const isPatient = userRole === 'patient';
            const assignedClinicianId = u.assigned_clinician_id;
            const assignedClinician = assignedClinicianId 
              ? clinicians.find(c => c.user_id === assignedClinicianId)
              : null;

            return (
              <div key={u.user_id} style={{
                display: 'grid', gridTemplateColumns: '60px 200px 100px 100px 100px 180px 200px',
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
                  backgroundColor: userRole === 'admin' ? '#E3F2FD' : userRole === 'clinician' ? '#E8F5E9' : '#FFF3E0',
                  color: userRole === 'admin' ? '#1565C0' : userRole === 'clinician' ? '#2E7D32' : '#E65100',
                }}>
                  {userRole}
                </div>
                <div style={typography.body}>{u.is_verified ? '✓ Verified' : 'Pending'}</div>
                <div style={typography.body}>{u.is_active ? '✓ Active' : '✗ Inactive'}</div>
                
                {/* Clinician Assignment Column */}
                <div>
                  {isPatient ? (
                    assigningPatient === u.user_id ? (
                      <div style={{ display: 'flex', gap: '4px' }}>
                        <select
                          value={selectedClinician || ''}
                          onChange={(e) => setSelectedClinician(Number(e.target.value))}
                          disabled={isSubmitting}
                          style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            border: `1px solid ${colors.neutral['300']}`,
                            fontSize: '12px',
                            flex: 1,
                          }}
                        >
                          <option value="">Select...</option>
                          {clinicians.map(c => (
                            <option key={c.user_id} value={c.user_id}>
                              {c.full_name || c.email}
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={() => selectedClinician && handleAssignClinician(u.user_id, selectedClinician)}
                          disabled={!selectedClinician || isSubmitting}
                          style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            border: 'none',
                            backgroundColor: selectedClinician ? colors.primary.default : colors.neutral['300'],
                            color: '#fff',
                            cursor: selectedClinician && !isSubmitting ? 'pointer' : 'not-allowed',
                            fontSize: '12px',
                          }}
                        >
                          ✓
                        </button>
                        <button
                          onClick={() => { setAssigningPatient(null); setSelectedClinician(null); }}
                          disabled={isSubmitting}
                          style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            border: `1px solid ${colors.neutral['300']}`,
                            backgroundColor: '#fff',
                            cursor: isSubmitting ? 'not-allowed' : 'pointer',
                            fontSize: '12px',
                          }}
                        >
                          ✗
                        </button>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {assignedClinician ? (
                          <span style={{ ...typography.caption, color: colors.neutral['700'] }}>
                            {assignedClinician.full_name || assignedClinician.email}
                          </span>
                        ) : (
                          <span style={{ ...typography.caption, color: colors.neutral['500'] }}>
                            Not assigned
                          </span>
                        )}
                        <button
                          onClick={() => {
                            setAssigningPatient(u.user_id);
                            setSelectedClinician(assignedClinicianId || null);
                            setAssignMessage('');
                          }}
                          disabled={isSubmitting}
                          style={{
                            padding: '2px 6px',
                            borderRadius: '4px',
                            border: 'none',
                            backgroundColor: '#E8F5E9',
                            color: '#2E7D32',
                            cursor: isSubmitting ? 'not-allowed' : 'pointer',
                            fontSize: '11px',
                            opacity: isSubmitting ? 0.5 : 1,
                          }}
                        >
                          Assign
                        </button>
                      </div>
                    )
                  ) : (
                    <span style={{ ...typography.caption, color: colors.neutral['500'] }}>—</span>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    onClick={() => handleEditUser(u)}
                    title="Edit User"
                    disabled={isSubmitting}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      border: 'none',
                      backgroundColor: '#E3F2FD',
                      color: '#1565C0',
                      cursor: isSubmitting ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '12px',
                      opacity: isSubmitting ? 0.5 : 1,
                    }}
                  >
                    <Edit2 size={14} /> Edit
                  </button>
                  <button
                    onClick={() => { setResetUserId(u.user_id); setResetMessage(''); }}
                    title="Reset Password"
                    disabled={isSubmitting}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      border: 'none',
                      backgroundColor: '#FFF3E0',
                      color: '#E65100',
                      cursor: isSubmitting ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '12px',
                      opacity: isSubmitting ? 0.5 : 1,
                    }}
                  >
                    <Key size={14} /> Reset PW
                  </button>
                  {u.is_active && u.user_id !== currentUser?.user_id && (
                    <button
                      onClick={() => handleDeactivate(u.user_id)}
                      title="Deactivate"
                      disabled={isSubmitting}
                      style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        border: 'none',
                        backgroundColor: '#FFEBEE',
                        color: '#C62828',
                        cursor: isSubmitting ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '12px',
                        opacity: isSubmitting ? 0.5 : 1,
                      }}
                    >
                      <XCircle size={14} /> Deactivate
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <p style={{ ...typography.caption, marginTop: '16px' }}>
          Showing {users.length} users. Admin users cannot view patient health data (PHI).
        </p>
      </main>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <MuiAlert onClose={() => setSnackbarOpen(false)} severity={snackbarSeverity} variant="filled">
          {snackbarMessage}
        </MuiAlert>
      </Snackbar>
    </div>
  );
};

export default AdminPage;
