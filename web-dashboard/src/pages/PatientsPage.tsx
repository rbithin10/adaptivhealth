/*
Patients list page.

Shows all patients being monitored. Displays their latest vital signs
and risk level. Clinicians can search for a patient or filter by risk level.
Click on a patient to see detailed information.
*/

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Search } from 'lucide-react';
import { api } from '../services/api';
import { User } from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';
import StatusBadge, { riskToStatus } from '../components/common/StatusBadge';

const PatientsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRisk, setFilterRisk] = useState<'all' | 'low' | 'moderate' | 'high'>('all');
  const [patients, setPatients] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    try {
      const usersList = await api.getAllUsers(1, 200);
      console.log('Loaded patients:', usersList);
      setPatients(usersList.users);
    } catch (error) {
      console.error('Error loading patients:', error);
      alert('Failed to load patients. Please make sure you are logged in.');
    } finally {
      setLoading(false);
    }
  };

  const filteredPatients = patients.filter((patient) => {
    const matchesSearch =
      (patient.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      patient.user_id.toString().includes(searchTerm);
    // TODO: Add risk level filtering once we have risk data
    // const matchesFilter = filterRisk === 'all' || patient.riskLevel === filterRisk;
    return matchesSearch;
  });

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
            onClick={() => navigate('/dashboard')}
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
            Back to Dashboard
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: '1440px', margin: '0 auto', padding: '32px' }}>
        <h1 style={typography.pageTitle}>Patient Management</h1>
        <p style={{ ...typography.body, color: colors.neutral['500'], marginBottom: '32px' }}>
          Monitor and manage all patients in your care team
        </p>

        {/* Filters Section */}
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
          {/* Search Bar */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ ...typography.body, fontWeight: 600, display: 'block', marginBottom: '8px' }}>
              Search Patients
            </label>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 16px',
                borderRadius: '8px',
                border: `1px solid ${colors.neutral['300']}`,
                backgroundColor: colors.neutral.white,
              }}
            >
              <Search size={20} color={colors.neutral['500']} />
              <input
                type="text"
                placeholder="Search by name or ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  flex: 1,
                  border: 'none',
                  outline: 'none',
                  fontSize: '14px',
                  fontFamily: 'inherit',
                }}
              />
            </div>
          </div>

          {/* Risk Filter */}
          <div>
            <label style={{ ...typography.body, fontWeight: 600, display: 'block', marginBottom: '8px' }}>
              Filter by Risk Level
            </label>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {['all', 'low', 'moderate', 'high'].map((level) => (
                <button
                  key={level}
                  onClick={() => setFilterRisk(level as any)}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '6px',
                    border: 'none',
                    backgroundColor:
                      filterRisk === level ? colors.primary.default : colors.neutral['100'],
                    color: filterRisk === level ? colors.neutral.white : colors.neutral['700'],
                    cursor: 'pointer',
                    fontWeight: 500,
                    textTransform: 'capitalize',
                    transition: 'all 0.2s',
                  }}
                >
                  {level === 'all' ? 'All Patients' : level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Patient List Table */}
        <div
          style={{
            backgroundColor: colors.neutral.white,
            border: `1px solid ${colors.neutral['300']}`,
            borderRadius: '12px',
            overflow: 'hidden',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}
        >
          {/* Table Header */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '200px 100px 100px 120px 100px 150px 80px',
              gap: '16px',
              padding: '16px 24px',
              backgroundColor: colors.neutral['50'],
              borderBottom: `1px solid ${colors.neutral['300']}`,
              fontWeight: 600,
              color: colors.neutral['700'],
              fontSize: '12px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            <div>Patient Name</div>
            <div>Age</div>
            <div>Gender</div>
            <div>Risk Level</div>
            <div>Heart Rate</div>
            <div>Last Reading</div>
            <div>Action</div>
          </div>

          {/* Table Rows */}
          {loading ? (
            <div style={{ padding: '48px', textAlign: 'center', color: colors.neutral['500'] }}>
              Loading patients...
            </div>
          ) : filteredPatients.length > 0 ? (
            filteredPatients.map((patient, idx) => (
              <div
                key={patient.user_id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '200px 100px 100px 120px 100px 150px 80px',
                  gap: '16px',
                  padding: '16px 24px',
                  borderBottom: idx < filteredPatients.length - 1 ? `1px solid ${colors.neutral['300']}` : 'none',
                  backgroundColor: idx % 2 === 0 ? colors.neutral.white : colors.neutral['50'],
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ ...typography.body, fontWeight: 600 }}>{patient.full_name}</div>
                </div>
                <div style={typography.body}>{patient.age || 'N/A'}</div>
                <div style={typography.body}>{patient.gender || 'N/A'}</div>
                <div>
                  <StatusBadge status="stable" size="sm" />
                </div>
                <div style={{ ...typography.body, fontWeight: 600 }}>
                  -- <span style={{ ...typography.caption, fontWeight: 400 }}>BPM</span>
                </div>
                <div style={typography.caption}>--</div>
                <button
                  onClick={() => navigate(`/patients/${patient.user_id}`)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '6px',
                    border: 'none',
                    backgroundColor: colors.primary.default,
                    color: colors.neutral.white,
                    cursor: 'pointer',
                    fontWeight: 500,
                    fontSize: '12px',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = colors.primary.dark;
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = colors.primary.default;
                  }}
                >
                  View
                </button>
              </div>
            ))
          ) : (
            <div
              style={{
                padding: '40px 24px',
                textAlign: 'center',
                color: colors.neutral['500'],
              }}
            >
              <p style={typography.body}>No patients found matching your criteria.</p>
            </div>
          )}
        </div>

        {/* Summary */}
        <div style={{ marginTop: '32px', display: 'flex', justifyContent: 'space-between' }}>
          <p style={typography.caption}>
            Showing {filteredPatients.length} of {patients.length} patients
          </p>
          <p style={typography.caption}>Total Active Patients: {patients.filter(p => p.is_active).length}</p>
        </div>
      </main>
    </div>
  );
};

export default PatientsPage;
