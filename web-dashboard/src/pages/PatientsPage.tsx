/*
Patients list page.

Shows all patients being monitored. Displays their latest vital signs
and risk level. Clinicians can search for a patient or filter by risk level.
Click on a patient to see detailed information.
*/

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Search } from 'lucide-react';
import { Snackbar, Alert as MuiAlert } from '@mui/material';
import { api } from '../services/api';
import { User, MedicalProfileSummary, MedicalProfile, VitalSignResponse } from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';
import StatusBadge, { riskToStatus } from '../components/common/StatusBadge';
import ClinicianTopBar from '../components/common/ClinicianTopBar';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://api.back-adaptivhealthuowd.xyz';

// What risk category a patient falls into
type PatientRiskLevel = 'low' | 'moderate' | 'high' | 'critical';

interface PatientRecordState {
  loaded: boolean;
  hasRecord: boolean;
  tip: 'empty' | 'missing' | null;
  url?: string;
  title?: string;
}

type RecordSource = Record<string, unknown>;
type PatientRow = User & { latest_vitals?: VitalSignResponse | null };

const PatientsPage: React.FC = () => {
  const navigate = useNavigate();
  // Search bar text and risk-level filter
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRisk, setFilterRisk] = useState<'all' | PatientRiskLevel>('all');
  // The full list of patients loaded from the server
  const [patients, setPatients] = useState<PatientRow[]>([]);
  const [loading, setLoading] = useState(true);
  // Toast notification state
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error'>('error');
  // Tracks which patient's medical record is currently being fetched
  const [recordsLoadingFor, setRecordsLoadingFor] = useState<number | null>(null);
  // Cached medical-record availability per patient
  const [recordsByPatient, setRecordsByPatient] = useState<Record<number, PatientRecordState>>({});
  // Document viewer modal state
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerUrl, setViewerUrl] = useState('');
  const [viewerTitle, setViewerTitle] = useState('Medical Record');
  const [viewerObjectUrl, setViewerObjectUrl] = useState<string | null>(null);
  const tableGridTemplate = 'minmax(140px,1.8fr) 52px 72px minmax(155px,1.6fr) 108px 88px 100px 80px 108px';
  const tableMinWidth = '1040px';

  const showSnackbar = (message: string, severity: 'success' | 'error') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  // Load patient list on first render
  useEffect(() => {
    loadPatients();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refresh medical record states when the tab regains focus
  // (catches documents uploaded on the detail page)
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible' && patients.length > 0) {
        hydrateMedicalRecordStates(patients);
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patients]);

  // Fetch all patients, their risk assessments, and medical record availability
  const loadPatients = async () => {
    try {
      const currentUser = await api.getCurrentUser();
      const currentRole = (currentUser.user_role || '').toLowerCase();
      if (currentRole !== 'clinician') {
        navigate('/dashboard');
        return;
      }

      const usersList = await api.getAllUsers(1, 200, 'patient');

      const patientUsers = (usersList.users || []).filter((userItem: User) => {
        const userRole = (userItem.user_role || '').toLowerCase();
        return userRole === 'patient';
      });

      // Fetch each patient's latest risk score in parallel
      const riskResults = await Promise.allSettled(
        patientUsers.map((patient) => api.getLatestRiskAssessmentForUser(patient.user_id))
      );

      // Fetch each patient's latest vitals in parallel
      const vitalsResults = await Promise.allSettled(
        patientUsers.map((patient) => api.getLatestVitalSignsForUser(patient.user_id))
      );

      const vitalsByPatientId: Record<number, VitalSignResponse | null> = {};
      vitalsResults.forEach((result, index) => {
        const patientId = patientUsers[index]?.user_id;
        if (patientId) {
          vitalsByPatientId[patientId] = result.status === 'fulfilled' ? result.value : null;
        }
      });

      const riskByPatientId: Record<number, { level: PatientRiskLevel; score: number }> = {};
      riskResults.forEach((result, index) => {
        const patientId = patientUsers[index]?.user_id;
        if (!patientId) return;

        const levelRaw = result.status === 'fulfilled'
          ? String(result.value?.risk_level ?? 'low').toLowerCase()
          : 'low';
        const level: PatientRiskLevel =
          levelRaw === 'moderate' || levelRaw === 'high' || levelRaw === 'critical'
            ? levelRaw
            : 'low';
        const score = result.status === 'fulfilled' ? Number(result.value?.risk_score ?? 0) : 0;

        riskByPatientId[patientId] = {
          level,
          score,
        };
      });

      setPatients(
        patientUsers.map((patient) => ({
          ...patient,
          risk_level: riskByPatientId[patient.user_id]?.level ?? 'low',
          risk_score: riskByPatientId[patient.user_id]?.score ?? 0,
          latest_vitals: vitalsByPatientId[patient.user_id] ?? null,
        }))
      );

      hydrateMedicalRecordStates(patientUsers);
    } catch (error) {
      console.error('Error loading patients:', error);
      showSnackbar('Failed to load patients. Please make sure you are logged in.', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Format a timestamp as "X min ago" or "X hr(s) ago"
  const formatTimeAgo = (isoDate?: string) => {
    if (!isoDate) return '--';
    const date = new Date(isoDate);
    const diffMs = Date.now() - date.getTime();
    const diffMin = Math.max(1, Math.floor(diffMs / 60000));
    if (diffMin < 60) return `${diffMin} min ago`;
    const diffHr = Math.floor(diffMin / 60);
    return `${diffHr} hr${diffHr > 1 ? 's' : ''} ago`;
  };

  // Show medical condition badges (e.g. Prior MI, Heart Failure) for a patient
  const renderMedicalSummary = (summary?: MedicalProfileSummary) => {
    const badges = summary
      ? [
          summary.has_prior_mi
            ? { label: 'Prior MI', backgroundColor: colors.critical.badge }
            : null,
          summary.has_heart_failure
            ? { label: 'Heart Failure', backgroundColor: colors.warning.badge }
            : null,
          summary.is_on_beta_blocker
            ? { label: 'β-blocker', backgroundColor: colors.primary.default }
            : null,
          summary.is_on_anticoagulant
            ? { label: 'Anticoagulant', backgroundColor: colors.warning.badge }
            : null,
        ].filter(Boolean) as { label: string; backgroundColor: string }[]
      : [];

    return (
      <div
        title="Derived from the patient’s documented medical history and active medications"
        style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {badges.length > 0 ? (
            badges.map((badge) => (
              <span
                key={badge.label}
                style={{
                  backgroundColor: badge.backgroundColor,
                  color: colors.neutral.white,
                  padding: '2px 8px',
                  borderRadius: '999px',
                  fontSize: '11px',
                  fontWeight: 600,
                }}
              >
                {badge.label}
              </span>
            ))
          ) : (
            <span style={{ fontSize: '11px', color: colors.neutral['500'] }}>No critical flags</span>
          )}
        </div>
        <div style={{ ...typography.caption, color: colors.neutral['500'] }}>
          {summary
            ? `${summary.active_condition_count} conditions · ${summary.active_medication_count} meds`
            : 'Awaiting medical data'}
        </div>
      </div>
    );
  };

  const normalizeRecordUrl = (url: string): string => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    if (url.startsWith('/')) {
      return `${API_BASE_URL}${url}`;
    }
    return `${API_BASE_URL}/${url}`;
  };

  const asRecord = (value: unknown): RecordSource | null => {
    return value && typeof value === 'object' ? (value as RecordSource) : null;
  };

  const getBooleanFlag = (source: unknown, keys: string[]): boolean | null => {
    const record = asRecord(source);
    if (!record) return null;

    for (const key of keys) {
      const value = record[key];
      if (typeof value === 'boolean') return value;
      if (typeof value === 'number') return value > 0;
      if (typeof value === 'string') {
        const normalized = value.trim().toLowerCase();
        if (normalized === 'true' || normalized === 'yes' || normalized === '1') return true;
        if (normalized === 'false' || normalized === 'no' || normalized === '0') return false;
      }
    }

    return null;
  };

  const extractDocumentEntries = (source: unknown): unknown[] => {
    const record = asRecord(source);
    if (!record) return [];

    const documentContainers: unknown[] = [
      record.uploaded_documents,
      record.documents,
      record.medical_documents,
      record.files,
      record.uploads,
      record.records,
    ];

    const entries: unknown[] = [];
    documentContainers.forEach((container) => {
      if (Array.isArray(container)) {
        entries.push(...container);
        return;
      }

      const nested = asRecord(container);
      if (!nested) return;

      const directUrlCandidate = [
        nested.url,
        nested.file_url,
        nested.document_url,
        nested.view_url,
        nested.download_url,
        nested.document_view_url,
        nested.viewer_url,
      ].some((value) => typeof value === 'string' && value.trim().length > 0);
      if (directUrlCandidate) {
        entries.push(nested);
      }

      const nestedArrays = [nested.items, nested.data, nested.results, nested.documents]
        .filter((value) => Array.isArray(value))
        .flatMap((value) => value as unknown[]);
      entries.push(...nestedArrays);
    });

    return entries;
  };

  const revokeViewerObjectUrl = () => {
    if (viewerObjectUrl) {
      URL.revokeObjectURL(viewerObjectUrl);
      setViewerObjectUrl(null);
    }
  };

  const closeViewer = () => {
    setViewerOpen(false);
    setViewerUrl('');
    revokeViewerObjectUrl();
  };

  // Open the in-page document viewer with a signed blob URL
  const openMedicalRecordViewer = async (url: string, title: string) => {
    revokeViewerObjectUrl();
    const blob = await api.getDocumentBlobByUrl(url);
    const objectUrl = URL.createObjectURL(blob);
    setViewerObjectUrl(objectUrl);
    setViewerUrl(objectUrl);
    setViewerTitle(title);
    setViewerOpen(true);
  };

  // Try to find a viewable document URL from the patient or medical profile
  const extractRecordUrl = (source: unknown): { url: string; title: string } | null => {
    const record = asRecord(source);
    if (!record) return null;

    if (record.file_available === false) {
      return null;
    }

    const urlKeys = [
      'url',
      'file_url',
      'document_url',
      'view_url',
      'document_view_url',
      'viewer_url',
      'download_url',
      'signed_url',
      'latest_document_url',
      'latest_uploaded_document_url',
      'latest_view_url',
      'medical_record_url',
      'record_url',
      'preview_url',
    ];
    for (const key of urlKeys) {
      const candidate = record[key];
      if (typeof candidate === 'string' && candidate.trim()) {
        const filename = typeof record.filename === 'string'
          ? record.filename
          : (typeof record.name === 'string' ? record.name : 'Medical Record');
        return {
          url: normalizeRecordUrl(candidate.trim()),
          title: filename,
        };
      }
    }

    const allDocumentItems = extractDocumentEntries(record);

    if (allDocumentItems.length > 0) {
      const availableCandidates = allDocumentItems
        .map((item) => asRecord(item))
        .filter((item): item is RecordSource => !!item)
        .filter((item) => item.file_available !== false);
      const latest = [...availableCandidates].sort((a, b) => {
        const aTime = new Date((a.uploaded_at as string) || (a.created_at as string) || 0).getTime();
        const bTime = new Date((b.uploaded_at as string) || (b.created_at as string) || 0).getTime();
        return bTime - aTime;
      })[0];
      if (!latest) return null;
      return extractRecordUrl(latest);
    }

    const nestedDocumentCandidates = [
      record.latest_uploaded_document,
      record.latest_document,
      record.latest_file,
      record.document,
      record.medical_record,
    ];

    for (const nested of nestedDocumentCandidates) {
      const extracted = extractRecordUrl(nested);
      if (extracted) return extracted;
    }

    return null;
  };

  const deriveRecordStateFromProfile = (profile: MedicalProfile): PatientRecordState => {
    const extracted = extractRecordUrl(profile);
    const uploadedDocs = Array.isArray(profile.uploaded_documents) ? profile.uploaded_documents : [];
    const uploadedFlag = getBooleanFlag(profile, ['has_uploaded_document', 'has_uploaded_documents']);
    const accessibleFlag = getBooleanFlag(profile, ['has_accessible_document', 'has_accessible_documents']);
    const hasUploaded = uploadedFlag ?? (uploadedDocs.length > 0);
    const hasAccessible = accessibleFlag ?? (uploadedDocs.some((doc) => doc.file_available !== false) || !!extracted);

    return {
      loaded: true,
      hasRecord: !!extracted,
      tip: hasUploaded && !hasAccessible ? 'missing' : (!hasUploaded ? 'empty' : null),
      url: extracted?.url,
      title: extracted?.title,
    };
  };

  // For each patient, check if a medical record document exists
  const hydrateMedicalRecordStates = async (patientsList: User[]) => {
    try {
    const results = await Promise.allSettled(
      patientsList.map((patient) => api.getPatientMedicalProfile(patient.user_id))
    );

    const nextState: Record<number, PatientRecordState> = {};

    results.forEach((result, index) => {
      const patient = patientsList[index];
      if (!patient) return;

      if (result.status === 'fulfilled') {
        nextState[patient.user_id] = deriveRecordStateFromProfile(result.value);
      } else {
        const summary = patient.medical_profile_summary;
        const hasUploadedDoc = getBooleanFlag(summary, ['has_uploaded_document', 'has_uploaded_documents']) ?? false;
        const hasAccessibleDoc = getBooleanFlag(summary, ['has_accessible_document', 'has_accessible_documents']) ?? false;
        nextState[patient.user_id] = {
          loaded: true,
          hasRecord: hasAccessibleDoc,
          tip: hasUploadedDoc && !hasAccessibleDoc ? 'missing' : (hasUploadedDoc ? null : 'empty'),
        };
      }
    });

    setRecordsByPatient(nextState);
    } catch (error) {
      console.warn('Could not preload medical record states:', error);
    }
  };

  const refreshRecordForPatient = async (patientId: number) => {
    try {
      const profile = await api.getPatientMedicalProfile(patientId);
      const derived = deriveRecordStateFromProfile(profile);
      setRecordsByPatient((prev) => ({ ...prev, [patientId]: derived }));
    } catch {
      // silently ignore; cached state remains
    }
  };

  // Open the document viewer for a specific patient's medical record
  const handleViewMedicalRecord = async (patient: User) => {
    setRecordsLoadingFor(patient.user_id);
    try {
      const cached = recordsByPatient[patient.user_id];
      if (cached?.url) {
        await openMedicalRecordViewer(
          cached.url,
          cached.title || `${patient.full_name || 'Patient'} — Medical Record`
        );
        return;
      }

      const directFromPatient = extractRecordUrl(patient);
      if (directFromPatient) {
        await openMedicalRecordViewer(
          directFromPatient.url,
          `${patient.full_name || 'Patient'} — ${directFromPatient.title}`
        );
        return;
      }

      const profile = await api.getPatientMedicalProfile(patient.user_id);
      const fromProfile = extractRecordUrl(profile);
      const derived = deriveRecordStateFromProfile(profile);
      setRecordsByPatient((prev) => ({
        ...prev,
        [patient.user_id]: derived,
      }));
      if (fromProfile) {
        await openMedicalRecordViewer(
          fromProfile.url,
          `${patient.full_name || 'Patient'} — ${fromProfile.title}`
        );
        return;
      }

      showSnackbar('Medical record is empty.', 'error');
    } catch (error) {
      console.error('Error loading medical record:', error);
      showSnackbar('Unable to open medical record.', 'error');
    } finally {
      setRecordsLoadingFor(null);
    }
  };

  const hasMedicalRecord = (patient: User): boolean => {
    const cached = recordsByPatient[patient.user_id];
    if (cached?.loaded) {
      return cached.hasRecord;
    }

    const summaryHasAccessibleDoc = getBooleanFlag(patient.medical_profile_summary, ['has_accessible_document', 'has_accessible_documents']);
    if (typeof summaryHasAccessibleDoc === 'boolean') {
      return summaryHasAccessibleDoc;
    }

    const summaryHasDoc = getBooleanFlag(patient.medical_profile_summary, ['has_uploaded_document', 'has_uploaded_documents']);
    if (typeof summaryHasDoc === 'boolean') {
      return summaryHasDoc;
    }
    return extractRecordUrl(patient) !== null;
  };

  const getMedicalRecordTip = (patient: User): 'empty' | 'missing' | null => {
    const cached = recordsByPatient[patient.user_id];
    if (cached?.loaded) {
      return cached.tip;
    }

    const summary = patient.medical_profile_summary;
    const hasUploaded = getBooleanFlag(summary, ['has_uploaded_document', 'has_uploaded_documents']);
    const hasAccessible = getBooleanFlag(summary, ['has_accessible_document', 'has_accessible_documents']);
    if (hasUploaded === true && hasAccessible === false) {
      return 'missing';
    }
    if (summary && hasUploaded === false) {
      return 'empty';
    }
    return null;
  };

  // Filter patients by search text and selected risk level
  const filteredPatients = patients.filter((patient) => {
    const userRole = (patient.user_role || '').toLowerCase();

    // Safety check to enforce patient-only rows
    if (userRole !== 'patient') {
      return false;
    }
    const matchesSearch =
      (patient.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      patient.user_id.toString().includes(searchTerm);
    // Filter by risk level when patient has risk data
    const patientRisk = patient.risk_level;
    const matchesFilter = filterRisk === 'all' || patientRisk === filterRisk;
    return matchesSearch && matchesFilter;
  });

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.neutral['50'] }}>
      <ClinicianTopBar />

      {/* Header */}
      <header
        style={{
          backgroundColor: colors.neutral.white,
          borderBottom: `1px solid ${colors.neutral['300']}`,
          padding: '12px 32px',
        }}
      >
        <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', alignItems: 'center', gap: '16px' }}>
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
      <main style={{ maxWidth: '1440px', margin: '0 auto', padding: '28px 32px' }}>
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
              {['all', 'low', 'moderate', 'high', 'critical'].map((level) => (
                <button
                  key={level}
                  onClick={() => setFilterRisk(level as 'all' | PatientRiskLevel)}
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
            overflowX: 'auto',
            overflowY: 'hidden',
            overscrollBehaviorX: 'contain',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}
        >
          {/* Table Header */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: tableGridTemplate,
              minWidth: tableMinWidth,
              gap: '12px',
              padding: '16px 20px',
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
            <div>Medical</div>
            <div>Risk Level</div>
            <div>Heart Rate</div>
            <div>Last Reading</div>
            <div style={{ textAlign: 'center' }}>Detail</div>
            <div style={{ textAlign: 'center' }}>Medical Records</div>
          </div>

          {/* Table Rows */}
          {loading ? (
            <div style={{ padding: '48px', textAlign: 'center', color: colors.neutral['500'] }}>
              Loading patients...
            </div>
          ) : filteredPatients.length > 0 ? (
            filteredPatients.map((patient, idx) => (
              (() => {
                const rowRecordState = recordsByPatient[patient.user_id];
                const isRowRecordLoading = recordsLoadingFor === patient.user_id;
                const canViewRowRecord = rowRecordState?.loaded ? rowRecordState.hasRecord : hasMedicalRecord(patient);

                return (
              <div
                key={patient.user_id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: tableGridTemplate,
                  minWidth: tableMinWidth,
                  gap: '12px',
                  padding: '16px 20px',
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
                <div>{renderMedicalSummary(patient.medical_profile_summary)}</div>
                <div>
                  <StatusBadge status={riskToStatus(patient.risk_level || 'low')} size="sm" />
                </div>
                <div style={{ ...typography.body, fontWeight: 600 }}>
                  {patient.latest_vitals?.heart_rate ?? '--'} <span style={{ ...typography.caption, fontWeight: 400 }}>BPM</span>
                </div>
                <div style={typography.caption}>
                  {formatTimeAgo(patient.latest_vitals?.timestamp)}
                </div>
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'flex-start',
                    gap: '4px',
                    minHeight: '42px',
                  }}
                >
                  <button
                    onClick={() => navigate(`/patients/${patient.user_id}`)}
                    style={{
                      minWidth: '84px',
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
                  <span style={{ ...typography.caption, fontSize: '11px', visibility: 'hidden' }}>
                    empty
                  </span>
                </div>
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'flex-start',
                    gap: '4px',
                    minHeight: '42px',
                  }}
                >
                  <button
                    onClick={() => canViewRowRecord
                      ? handleViewMedicalRecord(patient)
                      : refreshRecordForPatient(patient.user_id)
                    }
                    disabled={isRowRecordLoading}
                    style={{
                      minWidth: '84px',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: `1px solid ${canViewRowRecord ? colors.primary.default : colors.neutral['400']}`,
                      backgroundColor: colors.neutral.white,
                      color: canViewRowRecord ? colors.primary.default : colors.neutral['600'],
                      cursor: isRowRecordLoading ? 'not-allowed' : 'pointer',
                      fontWeight: 600,
                      fontSize: '12px',
                      opacity: isRowRecordLoading ? 0.65 : 1,
                    }}
                  >
                    {isRowRecordLoading ? 'Loading...' : (canViewRowRecord ? 'View' : 'Refresh')}
                  </button>
                  {getMedicalRecordTip(patient) && !isRowRecordLoading && (
                    <span style={{ ...typography.caption, color: colors.neutral['500'], fontSize: '11px' }}>
                      {getMedicalRecordTip(patient)}
                    </span>
                  )}
                </div>
              </div>
                );
              })()
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

      {viewerOpen && (
        <div
          onClick={closeViewer}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(17, 24, 39, 0.55)',
            zIndex: 1300,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 'min(1100px, 96vw)',
              height: 'min(760px, 92vh)',
              backgroundColor: colors.neutral.white,
              borderRadius: '12px',
              border: `1px solid ${colors.neutral['300']}`,
              boxShadow: '0 12px 30px rgba(0,0,0,0.2)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '14px 18px',
                borderBottom: `1px solid ${colors.neutral['300']}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
              }}
            >
              <div style={{ ...typography.body, fontWeight: 700, color: colors.neutral['800'] }}>
                {viewerTitle}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button
                  onClick={() => window.open(viewerUrl, '_blank', 'noopener,noreferrer')}
                  style={{
                    backgroundColor: colors.primary.default,
                    color: colors.neutral.white,
                    border: 'none',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Open in New Tab
                </button>
                <button
                  onClick={closeViewer}
                  style={{
                    backgroundColor: 'transparent',
                    color: colors.neutral['600'],
                    border: `1px solid ${colors.neutral['300']}`,
                    borderRadius: '6px',
                    padding: '6px 10px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Close
                </button>
              </div>
            </div>

            <iframe
              title={viewerTitle}
              src={viewerUrl}
              style={{ border: 'none', width: '100%', height: '100%' }}
            />
          </div>
        </div>
      )}

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

export default PatientsPage;
