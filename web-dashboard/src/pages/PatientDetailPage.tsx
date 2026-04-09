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
import { ArrowLeft, Heart, Wind, Activity, AlertTriangle, TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp, Zap, Crosshair, ArrowRight, Check, Loader, Shuffle, Clock, CheckCircle, MessageSquare, FileText, Info, RefreshCw, Eye, PenLine, Trash2 } from 'lucide-react';
import { Snackbar, Alert as MuiAlert } from '@mui/material';
import { api } from '../services/api';
import {
  AlertResponse,
  ActivitySessionResponse,
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
  ExplainPredictionResponse,
  MedicalProfile,
  MedicalExtractionStatusResponse,
  MedicalConditionCreate,
  MedicationCreate,
  DocumentUploadResponse,
  ClinicalNote,
} from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';
import StatusBadge, { riskToStatus } from '../components/common/StatusBadge';
import VitalsPanel from '../components/patient/VitalsPanel';
import MedicalProfilePanel from '../components/patient/MedicalProfilePanel';
import AlertsPanel from '../components/patient/AlertsPanel';
import SessionHistoryPanel from '../components/patient/SessionHistoryPanel';
import PredictionExplainabilityPanel from '../components/patient/PredictionExplainabilityPanel';
import AdvancedMLPanel from '../components/patient/AdvancedMLPanel';
import ClinicianTopBar from '../components/common/ClinicianTopBar';

type TimeRange = 'today' | '1week' | '2weeks' | '1month' | '3months';

// Convert the selected time range to a number of days for the API.
const rangeToDays = (range: TimeRange) => {
  switch (range) {
    case 'today':   return 7;
    case '2weeks':  return 14;
    case '1month':  return 30;
    case '3months': return 90;
    case '1week':
    default:        return 7;
  }
};

// Scale the page size so longer ranges actually return enough records.
const rangeToPerPage = (range: TimeRange): number => {
  switch (range) {
    case 'today':   return 300;
    case '1week':   return 500;
    case '2weeks':  return 1000;
    case '1month':  return 1000;
    case '3months': return 1000;
    default:        return 500;
  }
};

const PatientDetailPage: React.FC = () => {
  const { patientId } = useParams<{ patientId: string }>();
  const navigate = useNavigate();

  // Basic patient info and their latest readings
  const [patient, setPatient] = useState<User | null>(null);
  const [latestVitals, setLatestVitals] = useState<VitalSignResponse | null>(null);
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessmentResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [activities, setActivities] = useState<ActivitySessionResponse[]>([]);
  const [vitalsHistory, setVitalsHistory] = useState<VitalSignsHistoryResponse | null>(null);

  // Advanced ML feature states (anomaly detection, trend forecasting, etc.)
  const [anomalyData, setAnomalyData] = useState<AnomalyDetectionResponse | null>(null);
  const [anomalyHours, setAnomalyHours] = useState(24);
  const [anomalyExpanded, setAnomalyExpanded] = useState(true);
  const [anomalyPage, setAnomalyPage] = useState(1);
  const anomaliesPerPage = 5;
  const [trendData, setTrendData] = useState<TrendForecastResponse | null>(null);
  const [trendExpanded, setTrendExpanded] = useState(true);
  const [baselineData, setBaselineData] = useState<BaselineOptimizationResponse | null>(null);
  const [baselineExpanded, setBaselineExpanded] = useState(true);
  const [baselineApplyResult, setBaselineApplyResult] = useState<'success' | 'error' | null>(null);
  const [baselineApplying, setBaselineApplying] = useState(false);
  const [recData, setRecData] = useState<RankedRecommendationResponse | null>(null);
  const [recExpanded, setRecExpanded] = useState(true);

  // Natural-language AI summaries and model management
  const [riskSummaryData, setRiskSummaryData] = useState<NaturalLanguageRiskSummaryResponse | null>(null);
  const [nlSummaryLoading, setNlSummaryLoading] = useState(false);
  const [nlExpanded, setNlExpanded] = useState(true);
  const [clinicalNotes, setClinicalNotes] = useState<ClinicalNote[]>([]);
  const [newNoteText, setNewNoteText] = useState('');
  const [noteSubmitting, setNoteSubmitting] = useState(false);
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [editingNoteText, setEditingNoteText] = useState('');
  const [explainData, setExplainData] = useState<ExplainPredictionResponse | null>(null);
  const [explainExpanded, setExplainExpanded] = useState(true);
  const [explainLoading, setExplainLoading] = useState(false);
  // Selectable time range for vitals history chart
  const [timeRange, setTimeRange] = useState<TimeRange>('today');
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // Manual risk computation button state
  const [computingRisk, setComputingRisk] = useState(false);

  // Medical history: conditions and medications
  const [medicalProfile, setMedicalProfile] = useState<MedicalProfile | null>(null);
  const [medProfileExpanded, setMedProfileExpanded] = useState(true);
  const [showAddCondition, setShowAddCondition] = useState(false);
  const [showAddMedication, setShowAddMedication] = useState(false);
  const [newCondition, setNewCondition] = useState<MedicalConditionCreate>({ condition_type: 'prior_mi', condition_detail: '', status: 'active' });
  const [newMedication, setNewMedication] = useState<MedicationCreate>({ drug_class: 'beta_blocker', drug_name: '', dose: '', frequency: 'daily' });
  const [medProfileSaving, setMedProfileSaving] = useState(false);
  const [editingConditionId, setEditingConditionId] = useState<number | null>(null);
  const [editedCondition, setEditedCondition] = useState<Partial<MedicalConditionCreate>>({});
  const [editingMedicationId, setEditingMedicationId] = useState<number | null>(null);
  const [editedMedication, setEditedMedication] = useState<Partial<MedicationCreate>>({});

  // Document upload and AI-powered medical data extraction
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [medicalExtractionStatus, setMedicalExtractionStatus] = useState<MedicalExtractionStatusResponse | null>(null);
  const [extractionResult, setExtractionResult] = useState<DocumentUploadResponse | null>(null);
  const [showExtractionReview, setShowExtractionReview] = useState(false);
  const [editedExtraction, setEditedExtraction] = useState<{ conditions: MedicalConditionCreate[]; medications: MedicationCreate[] }>({ conditions: [], medications: [] });
  const [confirmingExtraction, setConfirmingExtraction] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error'>('error');

  const showSnackbar = (message: string, severity: 'success' | 'error') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  // Reload full patient data only when patient changes
  useEffect(() => {
    loadPatientData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  // Range switch should update only the history chart data, not the entire page payload.
  useEffect(() => {
    if (!patientId) return;
    const userId = Number(patientId);
    if (Number.isNaN(userId)) return;

    let cancelled = false;

    const loadHistoryForRange = async () => {
      try {
        const days = rangeToDays(timeRange);
        const history = await api.getVitalSignsHistoryForUser(
          userId,
          days,
          1,
          rangeToPerPage(timeRange),
        );
        if (!cancelled) {
          setVitalsHistory(history);
        }
      } catch {
        // Keep the existing chart data when range-specific fetch fails.
      }
    };

    void loadHistoryForRange();

    return () => {
      cancelled = true;
    };
  }, [patientId, timeRange]);

  // Lightweight refresh: fetches only vitals, history, alerts, and risk (4 calls).
  const refreshVitals = async () => {
    if (!patientId) return;
    const userId = Number(patientId);
    if (Number.isNaN(userId)) return;
    try {
      const days = rangeToDays(timeRange);
      const [latestResult, historyResult, alertsResult, riskResult] = await Promise.allSettled([
        api.getLatestVitalSignsForUser(userId),
        api.getVitalSignsHistoryForUser(userId, days, 1, rangeToPerPage(timeRange)),
        api.getAlertsForUser(userId, 1, 200),
        api.getLatestRiskAssessmentForUser(userId, {
          allowNotFound: true,
          requestSource: 'patient-detail-refresh',
        }),
      ]);
      if (latestResult.status === 'fulfilled') setLatestVitals(latestResult.value);
      if (historyResult.status === 'fulfilled') setVitalsHistory(historyResult.value);
      if (alertsResult.status === 'fulfilled') setAlerts(alertsResult.value.alerts || []);
      if (riskResult.status === 'fulfilled') setRiskAssessment(riskResult.value);
    } catch {
      // Silent — next poll or SSE event retries
    }
  };

  // Poll every 60s for routine vitals (batch-sync arrives every 5 min, so 60s is plenty).
  useEffect(() => {
    if (!patientId) return;
    const intervalId = setInterval(() => { void refreshVitals(); }, 60_000);
    return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId, timeRange]);

  // Production-safe mode: rely on polling on patient detail to avoid duplicate SSE clients.

  // Check if there's a pending document extraction job
  useEffect(() => {
    loadMedicalExtractionStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadMedicalExtractionStatus = async () => {
    try {
      const status = await api.getMedicalExtractionStatus();
      setMedicalExtractionStatus(status);
    } catch {
      setMedicalExtractionStatus(null);
    }
  };

  // Load all patient data in parallel (vitals, risk, alerts, ML features, etc.)
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
        api.getLatestRiskAssessmentForUser(userId, {
          allowNotFound: true,
          requestSource: 'patient-detail-load',
        }),
        api.getAlertsForUser(userId, 1, 200),
        api.getActivitiesForUser(userId, 5, 0),
        api.getVitalSignsHistoryForUser(userId, days, 1, rangeToPerPage(timeRange)),
        api.getAnomalyDetection(userId, anomalyHours),
        api.getTrendForecast(userId, days),
        api.getBaselineOptimization(userId, days),
        api.getRankedRecommendation(userId, riskAssessment?.risk_level || 'low'),
        api.getNaturalLanguageRiskSummary(userId),
        api.getPatientMedicalProfile(userId),
        api.getClinicalNotes(userId),
      ]);

      const [userResult, vitalsResult, riskResult, alertsResult, activitiesResult, historyResult, anomalyResult, trendResult, baselineResult, recRankResult, riskSummaryResult, medProfileResult, clinicalNotesResult] = results;
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
      } else {
        setRecData(null);
        // Don't push error - advanced ML features are optional
      }

      // Advanced ML: Natural Language Risk Summary
      if (riskSummaryResult.status === 'fulfilled') {
        setRiskSummaryData(riskSummaryResult.value);
      } else {
        setRiskSummaryData(null);
      }

      // Medical Profile
      if (medProfileResult.status === 'fulfilled') {
        setMedicalProfile(medProfileResult.value);
      } else {
        setMedicalProfile(null);
        // Don't push error - medical profile is optional (no data yet)
      }

      // Clinical Notes
      if (clinicalNotesResult.status === 'fulfilled') {
        setClinicalNotes(clinicalNotesResult.value);
      } else {
        setClinicalNotes([]);
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

  // Ask the server to run the AI risk assessment for this patient
  const handleComputeRisk = async () => {
    if (!patientId) return;
    const userId = Number(patientId);
    setComputingRisk(true);
    try {
      await api.computeRiskAssessmentForUser(userId);
      showSnackbar('AI assessment complete. Refreshing data...', 'success');
      await loadPatientData();
    } catch (err: any) {
      let detail = err?.response?.data?.detail || 'Unable to compute risk. The patient needs recent vitals submitted within the last 30 minutes.';
      if (err?.response?.status === 503) {
        detail = 'ML model not loaded on backend. Check backend logs, ensure model files exist in ml_models/, and restart the backend.';
      }
      showSnackbar(detail, 'error');
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
    if (diffHr < 24) return `${diffHr} hr${diffHr > 1 ? 's' : ''} ago`;

    const diffDays = Math.floor(diffHr / 24);
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    const diffWeeks = Math.floor(diffDays / 7);
    if (diffDays < 30) return `${diffWeeks} week${diffWeeks > 1 ? 's' : ''} ago`;

    const diffMonths = Math.floor(diffDays / 30);
    if (diffDays < 365) return `${diffMonths} month${diffMonths > 1 ? 's' : ''} ago`;

    const diffYears = Math.floor(diffDays / 365);
    return `${diffYears} year${diffYears > 1 ? 's' : ''} ago`;
  };

  // Parse risk factors from the JSON string stored in the assessment
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

  // Mark an alert as seen by the clinician
  const handleAcknowledgeAlert = async (alertId: number) => {
    try {
      await api.acknowledgeAlert(alertId);
      setAlerts((prev) => prev.map((alert) => (
        alert.alert_id === alertId ? { ...alert, acknowledged: true } : alert
      )));
      window.dispatchEvent(new Event('alerts:updated'));
      showSnackbar('Alert acknowledged successfully.', 'success');
    } catch (error) {
      showSnackbar('Failed to acknowledge alert.', 'error');
    }
  };

  // Close out an alert with resolution notes
  const handleResolveAlert = async (alertId: number) => {
    try {
      const resolved = await api.resolveAlert(alertId, {
        resolution_notes: 'Resolved by clinician from dashboard',
      });
      setAlerts((prev) => prev.map((alert) => (
        alert.alert_id === alertId ? { ...alert, ...resolved } : alert
      )));
      window.dispatchEvent(new Event('alerts:updated'));
      showSnackbar('Alert resolved successfully.', 'success');
    } catch (error) {
      showSnackbar('Failed to resolve alert.', 'error');
    }
  };

  // Generate a human-readable AI summary of the patient's risk
  const handleGenerateAiSummary = async (): Promise<void> => {
    if (!patientId) return;
    const userId = Number(patientId);
    setNlSummaryLoading(true);

    try {
      const summary = await api.getNaturalLanguageRiskSummary(userId);
      setRiskSummaryData(summary);
      showSnackbar('AI risk summary loaded.', 'success');
      return;
    } catch (error: any) {
      if (error?.response?.status === 404) {
        try {
          await api.computeRiskAssessmentForUser(userId);
          const summary = await api.getNaturalLanguageRiskSummary(userId);
          setRiskSummaryData(summary);
          showSnackbar('AI risk summary generated successfully.', 'success');
          return;
        } catch (innerError: any) {
          if (innerError?.response?.status === 503) {
            showSnackbar('Gemini is unavailable or not configured on backend. Set GEMINI_API_KEY and restart backend.', 'error');
            return;
          }
          showSnackbar('Unable to generate AI summary after risk computation. Check backend logs.', 'error');
          return;
        }
      }
      if (error?.response?.status === 503) {
        showSnackbar('Gemini is unavailable or not configured on backend. Set GEMINI_API_KEY and restart backend.', 'error');
        return;
      }
      showSnackbar(`Failed to load AI summary: ${error?.response?.data?.detail || error.message || 'Unknown error'}`, 'error');
    } finally {
      setNlSummaryLoading(false);
    }
  };

  // Clinical Notes handlers
  const handleAddNote = async (): Promise<void> => {
    if (!newNoteText.trim() || !patientId) return;
    setNoteSubmitting(true);
    try {
      await api.createClinicalNote(Number(patientId), newNoteText.trim());
      setNewNoteText('');
      const notes = await api.getClinicalNotes(Number(patientId));
      setClinicalNotes(notes);
    } catch (error) {
      showSnackbar('Failed to add note.', 'error');
    } finally {
      setNoteSubmitting(false);
    }
  };

  const handleUpdateNote = async (noteId: number): Promise<void> => {
    if (!editingNoteText.trim()) return;
    try {
      await api.updateClinicalNote(noteId, editingNoteText.trim());
      setEditingNoteId(null);
      setEditingNoteText('');
      const notes = await api.getClinicalNotes(Number(patientId));
      setClinicalNotes(notes);
    } catch (error) {
      showSnackbar('Failed to update note.', 'error');
    }
  };

  const handleDeleteNote = async (noteId: number): Promise<void> => {
    try {
      await api.deleteClinicalNote(noteId);
      const notes = await api.getClinicalNotes(Number(patientId));
      setClinicalNotes(notes);
    } catch (error) {
      showSnackbar('Failed to delete note.', 'error');
    }
  };

  // Run ML explainability to show which vitals drive the risk score
  const handleExplainPrediction = async (): Promise<void> => {
    if (!patient || !latestVitals) return;
    setExplainLoading(true);
    setExplainData(null);
    try {
      const result = await api.explainPrediction({
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
      setExplainData(result);
    } catch (error: any) {
      console.error('Explain prediction failed:', error);
      if (error?.response?.status === 503) {
        showSnackbar('ML model not loaded on backend. Please check backend logs and restart with model files present in ml_models/ folder.', 'error');
      } else {
        showSnackbar(`Failed to explain prediction: ${error?.response?.data?.detail || error.message || 'Unknown error'}`, 'error');
      }
    } finally {
      setExplainLoading(false);
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

  // Classify a vital reading as stable, warning, or critical
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

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.neutral['50'] }}>
      <ClinicianTopBar />

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
                {patient.gender?.charAt(0).toUpperCase()}{patient.gender?.slice(1) || 'N/A'}, {patient.age != null ? `${patient.age} years old` : 'Age not set'}
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

        <VitalsPanel
          latestVitals={latestVitals}
          vitalsHistory={vitalsHistory}
          timeRange={timeRange}
          setTimeRange={setTimeRange}
          riskAssessment={riskAssessment}
          computingRisk={computingRisk}
          onComputeRisk={handleComputeRisk}
          getVitalStatus={getVitalStatus}
        />


        {/* ================================================================= */}
        {/* AI Risk Summary Panel                                             */}
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
              <span style={{ ...typography.sectionTitle, margin: 0 }}>AI Risk Summary</span>
            </div>
            {nlExpanded ? <ChevronUp size={20} color={colors.neutral['500']} /> : <ChevronDown size={20} color={colors.neutral['500']} />}
          </button>

          {nlExpanded && (
            <div style={{ padding: '24px' }}>

              {/* Patient Risk Summary */}
              <div style={{ marginBottom: '28px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                  <FileText size={18} color={colors.neutral['600']} />
                  <span style={{ fontSize: '15px', fontWeight: 700, color: colors.neutral['700'] }}>Patient Risk Summary</span>
                  <button
                    onClick={handleGenerateAiSummary}
                    disabled={nlSummaryLoading}
                    style={{
                      marginLeft: 'auto',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      backgroundColor: nlSummaryLoading ? colors.neutral['300'] : colors.primary.default,
                      color: colors.neutral.white,
                      border: 'none',
                      borderRadius: '8px',
                      cursor: nlSummaryLoading ? 'not-allowed' : 'pointer',
                      fontSize: '12px',
                      fontWeight: 600,
                    }}
                  >
                    <RefreshCw size={14} />
                    {nlSummaryLoading ? 'Generating...' : 'Generate AI Summary'}
                  </button>
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
                    {/* Row 1: Key metrics */}
                    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' as const, alignItems: 'center', marginBottom: '16px' }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        padding: '4px 12px',
                        borderRadius: '999px',
                        fontSize: '12px',
                        fontWeight: 700,
                        textTransform: 'uppercase' as const,
                        letterSpacing: '0.5px',
                        backgroundColor:
                          riskSummaryData.risk_level === 'critical' || riskSummaryData.risk_level === 'high'
                            ? colors.critical.badge
                            : riskSummaryData.risk_level === 'moderate'
                            ? colors.warning.badge
                            : colors.stable.badge,
                        color: colors.neutral.white,
                      }}>
                        {riskSummaryData.risk_level}
                      </span>

                      <div style={{ display: 'flex', flexDirection: 'column' as const }}>
                        <span style={{ fontSize: '11px', fontWeight: 600, color: colors.neutral['500'], textTransform: 'uppercase' as const, letterSpacing: '0.4px' }}>Risk Score</span>
                        <span style={{ fontSize: '22px', fontWeight: 700, color: colors.neutral['800'], lineHeight: 1.2 }}>
                          {(riskSummaryData.risk_score * 100).toFixed(0)}%
                        </span>
                      </div>

                      {riskAssessment?.confidence != null && (() => {
                        const pct = riskAssessment.confidence * 100;
                        const band = pct >= 85 ? 'High reliability' : pct >= 70 ? 'Moderate reliability' : 'Low reliability';
                        const bandColor = pct >= 85 ? colors.stable.text : pct >= 70 ? colors.warning.text : colors.critical.text;
                        const bandBg = pct >= 85 ? colors.stable.background : pct >= 70 ? colors.warning.background : colors.critical.background;
                        return (
                          <div style={{ display: 'flex', flexDirection: 'column' as const }}>
                            <span style={{ fontSize: '11px', fontWeight: 600, color: colors.neutral['500'], textTransform: 'uppercase' as const, letterSpacing: '0.4px' }}>Assessment Reliability</span>
                            <span style={{
                              display: 'inline-block',
                              marginTop: '4px',
                              padding: '3px 10px',
                              borderRadius: '999px',
                              fontSize: '13px',
                              fontWeight: 700,
                              color: bandColor,
                              backgroundColor: bandBg,
                            }}>
                              {band}
                            </span>
                          </div>
                        );
                      })()}

                      {riskAssessment != null && (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          padding: '4px 10px',
                          borderRadius: '999px',
                          fontSize: '12px',
                          fontWeight: 600,
                          backgroundColor: riskAssessment.alert_triggered ? colors.critical.background : colors.stable.background,
                          border: `1px solid ${riskAssessment.alert_triggered ? colors.critical.border : colors.stable.border}`,
                          color: riskAssessment.alert_triggered ? colors.critical.text : colors.stable.text,
                        }}>
                          <AlertTriangle size={12} />
                          {riskAssessment.alert_triggered ? 'Alert Triggered' : 'No Alert'}
                        </span>
                      )}

                      {riskSummaryData.assessment_date && (
                        <span style={{ marginLeft: 'auto', fontSize: '12px', color: colors.neutral['500'] }}>
                          Assessed {new Date(riskSummaryData.assessment_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>

                    {/* Row 2: AI narrative */}
                    <div style={{ marginBottom: '20px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, color: colors.neutral['500'], textTransform: 'uppercase' as const, letterSpacing: '0.5px', marginBottom: '8px' }}>
                        AI Summary
                      </div>
                      <p style={{
                        ...typography.body,
                        lineHeight: '1.75',
                        color: colors.neutral['800'],
                        margin: 0,
                        fontSize: '15px',
                        padding: '14px 16px',
                        backgroundColor: 'rgba(255,255,255,0.55)',
                        borderRadius: '8px',
                      }}>
                        {riskSummaryData.plain_summary}
                      </p>
                    </div>

                    {/* Row 3: 2-column detail grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>

                      {/* Left: Primary Concern + Contributing Factors */}
                      <div style={{
                        padding: '14px 16px',
                        backgroundColor: 'rgba(255,255,255,0.55)',
                        borderRadius: '8px',
                        display: 'flex',
                        flexDirection: 'column' as const,
                        gap: '12px',
                      }}>
                        {riskAssessment?.primary_concern && (
                          <div>
                            <div style={{ fontSize: '11px', fontWeight: 700, color: colors.neutral['500'], textTransform: 'uppercase' as const, letterSpacing: '0.5px', marginBottom: '6px' }}>
                              Primary Concern
                            </div>
                            <div style={{ fontSize: '14px', fontWeight: 600, color: colors.neutral['800'] }}>
                              {riskAssessment.primary_concern}
                            </div>
                          </div>
                        )}

                        {riskFactors.length > 0 && (
                          <div>
                            <div style={{ fontSize: '11px', fontWeight: 700, color: colors.neutral['500'], textTransform: 'uppercase' as const, letterSpacing: '0.5px', marginBottom: '8px' }}>
                              Contributing Factors
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column' as const, gap: '6px' }}>
                              {riskFactors.map((factor: string, i: number) => (
                                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                                  <span style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    width: '18px',
                                    height: '18px',
                                    borderRadius: '50%',
                                    backgroundColor:
                                      riskSummaryData.risk_level === 'critical' || riskSummaryData.risk_level === 'high'
                                        ? colors.critical.badge
                                        : riskSummaryData.risk_level === 'moderate'
                                        ? colors.warning.badge
                                        : colors.stable.badge,
                                    color: colors.neutral.white,
                                    fontSize: '10px',
                                    fontWeight: 700,
                                    flexShrink: 0,
                                    marginTop: '2px',
                                  }}>
                                    {i + 1}
                                  </span>
                                  <span style={{ fontSize: '13px', color: colors.neutral['700'], lineHeight: '1.5' }}>
                                    {factor}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {!riskAssessment?.primary_concern && riskFactors.length === 0 && (
                          <span style={{ fontSize: '13px', color: colors.neutral['400'], fontStyle: 'italic' }}>
                            No factors available for this assessment.
                          </span>
                        )}
                      </div>

                      {/* Right: Vitals Used */}
                      <div style={{
                        padding: '14px 16px',
                        backgroundColor: 'rgba(255,255,255,0.55)',
                        borderRadius: '8px',
                      }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: colors.neutral['500'], textTransform: 'uppercase' as const, letterSpacing: '0.5px', marginBottom: '10px' }}>
                          Vitals Used in Assessment
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column' as const, gap: '8px' }}>
                          {riskAssessment?.input_heart_rate != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '13px', color: colors.neutral['600'] }}>Heart Rate</span>
                              <span style={{ fontSize: '14px', fontWeight: 700, color: colors.neutral['800'] }}>
                                {riskAssessment.input_heart_rate} <span style={{ fontSize: '11px', fontWeight: 400, color: colors.neutral['500'] }}>bpm</span>
                              </span>
                            </div>
                          )}
                          {riskAssessment?.input_spo2 != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '13px', color: colors.neutral['600'] }}>SpO₂</span>
                              <span style={{ fontSize: '14px', fontWeight: 700, color: colors.neutral['800'] }}>
                                {riskAssessment.input_spo2}<span style={{ fontSize: '11px', fontWeight: 400, color: colors.neutral['500'] }}>%</span>
                              </span>
                            </div>
                          )}
                          {riskAssessment?.input_hrv != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '13px', color: colors.neutral['600'] }}>HRV</span>
                              <span style={{ fontSize: '14px', fontWeight: 700, color: colors.neutral['800'] }}>
                                {riskAssessment.input_hrv} <span style={{ fontSize: '11px', fontWeight: 400, color: colors.neutral['500'] }}>ms</span>
                              </span>
                            </div>
                          )}
                          {riskAssessment?.input_blood_pressure_sys != null && riskAssessment?.input_blood_pressure_dia != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '13px', color: colors.neutral['600'] }}>Blood Pressure</span>
                              <span style={{ fontSize: '14px', fontWeight: 700, color: colors.neutral['800'] }}>
                                {riskAssessment.input_blood_pressure_sys}/{riskAssessment.input_blood_pressure_dia} <span style={{ fontSize: '11px', fontWeight: 400, color: colors.neutral['500'] }}>mmHg</span>
                              </span>
                            </div>
                          )}
                          {riskAssessment?.input_heart_rate == null &&
                           riskAssessment?.input_spo2 == null &&
                           riskAssessment?.input_hrv == null &&
                           riskAssessment?.input_blood_pressure_sys == null && (
                            <span style={{ fontSize: '13px', color: colors.neutral['400'], fontStyle: 'italic' }}>
                              No input vitals recorded for this assessment.
                            </span>
                          )}
                        </div>
                      </div>

                    </div>
                  </div>
                ) : (
                  <div style={{
                    padding: '20px',
                    textAlign: 'center' as const,
                    backgroundColor: colors.neutral['50'],
                    borderRadius: '8px',
                    color: colors.neutral['500'],
                  }}>
                    No summary available yet. Click "Generate AI Summary" to compute and load insights.
                  </div>
                )}
              </div>

              {/* Divider */}
              <div style={{ height: '1px', backgroundColor: colors.neutral['200'], marginBottom: '28px' }} />

              {/* Clinician Notes */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                  <PenLine size={18} color={colors.neutral['600']} />
                  <span style={{ fontSize: '15px', fontWeight: 700, color: colors.neutral['700'] }}>Clinician Notes</span>
                </div>

                {clinicalNotes.length > 0 ? (
                  <div style={{
                    border: `1px solid ${colors.neutral['200']}`,
                    borderRadius: '10px',
                    overflow: 'hidden',
                    marginBottom: '20px',
                  }}>
                    {clinicalNotes.map((note, idx) => (
                      <div
                        key={note.note_id}
                        style={{
                          padding: '16px 20px',
                          backgroundColor: idx % 2 === 0 ? colors.neutral.white : colors.neutral['50'],
                          borderBottom: idx < clinicalNotes.length - 1 ? `1px solid ${colors.neutral['200']}` : 'none',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '2px 8px',
                              borderRadius: '999px',
                              fontSize: '11px',
                              fontWeight: 700,
                              backgroundColor: '#EEF2FF',
                              color: colors.primary.default,
                              letterSpacing: '0.3px',
                            }}>
                              Clinician Note
                            </span>
                            <span style={{ fontSize: '13px', color: colors.neutral['500'] }}>
                              {note.clinician_name || 'Clinician'} · {new Date(note.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                            <button
                              onClick={() => { setEditingNoteId(note.note_id); setEditingNoteText(note.content); }}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                padding: '4px 8px',
                                fontSize: '12px',
                                color: colors.neutral['600'],
                                backgroundColor: 'transparent',
                                border: `1px solid ${colors.neutral['300']}`,
                                borderRadius: '6px',
                                cursor: 'pointer',
                              }}
                            >
                              <PenLine size={12} /> Edit
                            </button>
                            <button
                              onClick={() => handleDeleteNote(note.note_id)}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                padding: '4px 8px',
                                fontSize: '12px',
                                color: colors.critical.text,
                                backgroundColor: 'transparent',
                                border: `1px solid ${colors.critical.border}`,
                                borderRadius: '6px',
                                cursor: 'pointer',
                              }}
                            >
                              <Trash2 size={12} /> Delete
                            </button>
                          </div>
                        </div>

                        {editingNoteId === note.note_id ? (
                          <div>
                            <textarea
                              value={editingNoteText}
                              onChange={(e) => setEditingNoteText(e.target.value)}
                              style={{
                                width: '100%',
                                minHeight: '80px',
                                padding: '10px 12px',
                                border: `1px solid ${colors.neutral['300']}`,
                                borderRadius: '8px',
                                fontSize: '14px',
                                resize: 'vertical' as const,
                                fontFamily: 'inherit',
                                marginBottom: '8px',
                                boxSizing: 'border-box' as const,
                              }}
                            />
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button
                                onClick={() => handleUpdateNote(note.note_id)}
                                style={{
                                  padding: '6px 14px',
                                  backgroundColor: colors.primary.default,
                                  color: colors.neutral.white,
                                  border: 'none',
                                  borderRadius: '8px',
                                  cursor: 'pointer',
                                  fontSize: '13px',
                                  fontWeight: 600,
                                }}
                              >
                                Save
                              </button>
                              <button
                                onClick={() => { setEditingNoteId(null); setEditingNoteText(''); }}
                                style={{
                                  padding: '6px 14px',
                                  backgroundColor: 'transparent',
                                  color: colors.neutral['600'],
                                  border: `1px solid ${colors.neutral['300']}`,
                                  borderRadius: '8px',
                                  cursor: 'pointer',
                                  fontSize: '13px',
                                }}
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <p style={{
                            ...typography.body,
                            margin: 0,
                            fontSize: '14px',
                            color: colors.neutral['700'],
                            lineHeight: '1.65',
                            whiteSpace: 'pre-wrap' as const,
                          }}>
                            {note.content}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{
                    padding: '16px 20px',
                    textAlign: 'center' as const,
                    color: colors.neutral['400'],
                    fontSize: '14px',
                    fontStyle: 'italic',
                    backgroundColor: colors.neutral['50'],
                    borderRadius: '8px',
                    marginBottom: '20px',
                    border: `1px dashed ${colors.neutral['300']}`,
                  }}>
                    No notes yet. Add the first clinical observation below.
                  </div>
                )}

                <div style={{
                  border: `1px solid ${colors.neutral['200']}`,
                  borderRadius: '10px',
                  padding: '16px',
                  backgroundColor: colors.neutral['50'],
                }}>
                  <textarea
                    id="clinician-note-textarea"
                    value={newNoteText}
                    onChange={(e) => setNewNoteText(e.target.value)}
                    placeholder="Add clinical observation..."
                    style={{
                      width: '100%',
                      minHeight: '90px',
                      padding: '10px 12px',
                      border: `1px solid ${colors.neutral['300']}`,
                      borderRadius: '8px',
                      fontSize: '14px',
                      resize: 'vertical' as const,
                      fontFamily: 'inherit',
                      backgroundColor: colors.neutral.white,
                      boxSizing: 'border-box' as const,
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '12px', color: colors.neutral['400'] }}>
                      <Info size={12} /> Included in future AI summaries
                    </span>
                    <button
                      onClick={handleAddNote}
                      disabled={noteSubmitting || !newNoteText.trim()}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '8px 16px',
                        backgroundColor: noteSubmitting || !newNoteText.trim() ? colors.neutral['300'] : colors.primary.default,
                        color: colors.neutral.white,
                        border: 'none',
                        borderRadius: '8px',
                        cursor: noteSubmitting || !newNoteText.trim() ? 'not-allowed' : 'pointer',
                        fontSize: '13px',
                        fontWeight: 600,
                      }}
                    >
                      {noteSubmitting ? 'Adding...' : 'Add Note'}
                    </button>
                  </div>
                </div>
              </div>

            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* Medical Profile Panel                                           */}
        {/* ================================================================= */}
        <MedicalProfilePanel
          patientId={Number(patientId)}
          medicalProfile={medicalProfile}
          expanded={medProfileExpanded}
          onToggle={() => setMedProfileExpanded(!medProfileExpanded)}
        >
              {/* AI Flags Banner */}
              {medicalProfile && (medicalProfile.has_prior_mi || medicalProfile.has_heart_failure || medicalProfile.is_on_beta_blocker || medicalProfile.is_on_anticoagulant) && (
                <div style={{
                  backgroundColor: colors.warning.background,
                  border: `1px solid ${colors.warning.border}`,
                  borderRadius: '8px',
                  padding: '12px 16px',
                  marginBottom: '20px',
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '8px',
                  alignItems: 'center',
                }}>
                  <AlertTriangle size={16} color={colors.warning.text} />
                  <span style={{ ...typography.caption, fontWeight: 700, color: colors.warning.text }}>AI Flags:</span>
                  {medicalProfile.has_prior_mi && (
                    <span style={{ backgroundColor: colors.critical.badge, color: '#fff', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px' }}>
                      Prior MI (+0.10 risk)
                    </span>
                  )}
                  {medicalProfile.has_heart_failure && (
                    <span style={{ backgroundColor: colors.critical.badge, color: '#fff', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px' }}>
                      Heart Failure {medicalProfile.heart_failure_class ? `NYHA ${medicalProfile.heart_failure_class}` : ''}
                    </span>
                  )}
                  {medicalProfile.is_on_beta_blocker && (
                    <span style={{ backgroundColor: colors.primary.default, color: '#fff', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px' }}>
                      Beta-Blocker (HR adjusted)
                    </span>
                  )}
                  {medicalProfile.is_on_anticoagulant && (
                    <span style={{ backgroundColor: colors.warning.badge, color: '#fff', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px' }}>
                      Anticoagulant (fall risk)
                    </span>
                  )}
                  {medicalProfile.is_on_antiplatelet && (
                    <span style={{ backgroundColor: colors.stable.badge, color: '#fff', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px' }}>
                      On Antiplatelet
                    </span>
                  )}
                </div>
              )}

              {/* Document Upload Section */}
              <div style={{ marginBottom: '20px', display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                {medicalExtractionStatus && (
                  <span
                    style={{
                      backgroundColor: medicalExtractionStatus.ready ? colors.stable.background : colors.critical.background,
                      color: medicalExtractionStatus.ready ? colors.stable.text : colors.critical.text,
                      border: `1px solid ${medicalExtractionStatus.ready ? colors.stable.badge : colors.critical.border}`,
                      borderRadius: '999px',
                      padding: '4px 10px',
                      fontSize: '11px',
                      fontWeight: 700,
                    }}
                  >
                    {medicalExtractionStatus.ready ? 'AI READY' : 'AI NOT READY'}
                  </span>
                )}
                <label style={{
                  backgroundColor: '#6B21A8',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px 16px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: uploadingDoc ? 'not-allowed' : 'pointer',
                  opacity: uploadingDoc ? 0.6 : 1,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}>
                  {uploadingDoc ? <Loader size={14} className="spin" /> : <FileText size={14} />}
                  {uploadingDoc ? 'Extracting...' : 'Upload Document (AI Extract)'}
                  <input
                    type="file"
                    accept=".pdf,.txt"
                    style={{ display: 'none' }}
                    disabled={uploadingDoc}
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file || !patientId) return;
                      e.target.value = '';
                      if (file.size > 5 * 1024 * 1024) {
                        showSnackbar('File too large. Maximum 5MB.', 'error');
                        return;
                      }
                      setUploadingDoc(true);
                      try {
                        const result = await api.uploadPatientDocument(Number(patientId), file);
                        setExtractionResult(result);
                        setEditedExtraction({
                          conditions: result.extracted_conditions || [],
                          medications: result.extracted_medications || [],
                        });
                        setShowExtractionReview(true);
                        // Refresh profile so the status badge updates
                        if (patientId) {
                          const updated = await api.getPatientMedicalProfile(Number(patientId));
                          setMedicalProfile(updated);
                        }
                      } catch (err: any) {
                        showSnackbar(err?.response?.data?.detail || 'Upload failed', 'error');
                      } finally {
                        setUploadingDoc(false);
                      }
                    }}
                  />
                </label>
                {/* Document status badge */}
                {(() => {
                  const latestDoc = medicalProfile?.uploaded_documents?.find(
                    (d) => d.file_available !== false
                  ) ?? medicalProfile?.uploaded_documents?.[0];
                  const hasDoc = !!latestDoc && latestDoc.file_available !== false;
                  return (
                    <>
                      <span
                        style={{
                          backgroundColor: hasDoc ? colors.stable.background : colors.neutral['100'],
                          color: hasDoc ? colors.stable.text : colors.neutral['500'],
                          border: `1px solid ${hasDoc ? colors.stable.badge : colors.neutral['300']}`,
                          borderRadius: '999px',
                          padding: '4px 10px',
                          fontSize: '11px',
                          fontWeight: 700,
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {hasDoc ? '✓ Document Uploaded' : 'Empty'}
                      </span>
                      {hasDoc && latestDoc && (
                        <button
                          onClick={async () => {
                            try {
                              // view_url is /api/v1/… but Axios baseURL already includes /api/v1,
                              // so strip the prefix to avoid doubling it in the request path.
                              const relPath = latestDoc.view_url.replace(/^\/api\/v1/, '');
                              const blob = await api.getDocumentBlobByUrl(relPath);
                              const objectUrl = URL.createObjectURL(blob);
                              window.open(objectUrl, '_blank', 'noopener,noreferrer');
                              setTimeout(() => URL.revokeObjectURL(objectUrl), 30000);
                            } catch {
                              showSnackbar('Could not open document. File may be unavailable.', 'error');
                            }
                          }}
                          style={{
                            backgroundColor: 'transparent',
                            color: colors.primary.default,
                            border: `1px solid ${colors.primary.default}`,
                            borderRadius: '6px',
                            padding: '6px 14px',
                            fontSize: '13px',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          <Eye size={13} /> View File
                        </button>
                      )}
                    </>
                  );
                })()}
                <span style={{ ...typography.caption, color: colors.neutral['500'] }}>
                  PDF or TXT, max 5MB — AI extracts conditions & medications for review
                  {medicalExtractionStatus && !medicalExtractionStatus.ready
                    ? ' (Configure GEMINI_API_KEY and restart backend)'
                    : ''}
                </span>
              </div>

              {medicalProfile?.has_document_storage_warning && (
                <div
                  style={{
                    marginBottom: '14px',
                    backgroundColor: colors.warning.background,
                    border: `1px solid ${colors.warning.badge}`,
                    color: colors.warning.text,
                    borderRadius: '8px',
                    padding: '10px 12px',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}
                >
                  {medicalProfile.missing_document_count || 0} uploaded document(s) are missing from storage. Re-upload to restore viewing.
                </div>
              )}

              {/* Extraction Review Panel */}
              {showExtractionReview && extractionResult && (
                <div style={{
                  backgroundColor: '#F5F3FF',
                  border: '1px solid #C4B5FD',
                  borderRadius: '8px',
                  padding: '16px 20px',
                  marginBottom: '20px',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <span style={{ ...typography.body, fontWeight: 700, color: '#6B21A8' }}>
                      AI Extraction Review — {extractionResult.filename}
                    </span>
                    <button onClick={() => setShowExtractionReview(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: colors.neutral['500'], fontSize: '18px' }}>✕</button>
                  </div>
                  <p style={{ ...typography.caption, color: colors.neutral['600'], marginBottom: '12px' }}>
                    {extractionResult.extraction_message}
                  </p>

                  {/* Extracted Conditions */}
                  {editedExtraction.conditions.length > 0 && (
                    <div style={{ marginBottom: '12px' }}>
                      <span style={{ ...typography.caption, fontWeight: 700 }}>Extracted Conditions ({editedExtraction.conditions.length})</span>
                      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '6px', fontSize: '13px' }}>
                        <thead>
                          <tr style={{ borderBottom: `1px solid ${colors.neutral['300']}` }}>
                            <th style={{ textAlign: 'left', padding: '6px 8px' }}>Type</th>
                            <th style={{ textAlign: 'left', padding: '6px 8px' }}>Detail</th>
                            <th style={{ textAlign: 'left', padding: '6px 8px' }}>Status</th>
                            <th style={{ padding: '6px 8px', width: '40px' }}></th>
                          </tr>
                        </thead>
                        <tbody>
                          {editedExtraction.conditions.map((c, i) => (
                            <tr key={i} style={{ borderBottom: `1px solid ${colors.neutral['200']}` }}>
                              <td style={{ padding: '6px 8px' }}>
                                <select value={c.condition_type} onChange={e => {
                                  const updated = [...editedExtraction.conditions];
                                  updated[i] = { ...updated[i], condition_type: e.target.value };
                                  setEditedExtraction({ ...editedExtraction, conditions: updated });
                                }} style={{ fontSize: '12px', padding: '4px', borderRadius: '4px', border: `1px solid ${colors.neutral['300']}` }}>
                                  {['prior_mi','cabg','pci_stent','heart_failure','valve_disease','atrial_fibrillation','other_arrhythmia','hypertension','diabetes_type1','diabetes_type2','dyslipidemia','ckd','copd','pad','stroke_tia','smoking','family_cvd','obesity','other'].map(t => <option key={t} value={t}>{t.replace(/_/g,' ')}</option>)}
                                </select>
                              </td>
                              <td style={{ padding: '6px 8px' }}>
                                <input value={c.condition_detail || ''} onChange={e => {
                                  const updated = [...editedExtraction.conditions];
                                  updated[i] = { ...updated[i], condition_detail: e.target.value };
                                  setEditedExtraction({ ...editedExtraction, conditions: updated });
                                }} style={{ width: '100%', fontSize: '12px', padding: '4px', borderRadius: '4px', border: `1px solid ${colors.neutral['300']}` }} />
                              </td>
                              <td style={{ padding: '6px 8px' }}>
                                <select value={c.status || 'active'} onChange={e => {
                                  const updated = [...editedExtraction.conditions];
                                  updated[i] = { ...updated[i], status: e.target.value };
                                  setEditedExtraction({ ...editedExtraction, conditions: updated });
                                }} style={{ fontSize: '12px', padding: '4px', borderRadius: '4px', border: `1px solid ${colors.neutral['300']}` }}>
                                  <option value="active">Active</option>
                                  <option value="managed">Managed</option>
                                  <option value="resolved">Resolved</option>
                                </select>
                              </td>
                              <td style={{ padding: '6px 8px' }}>
                                <button onClick={() => {
                                  const updated = editedExtraction.conditions.filter((_, idx) => idx !== i);
                                  setEditedExtraction({ ...editedExtraction, conditions: updated });
                                }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: colors.critical.badge, fontSize: '16px' }}>✕</button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Extracted Medications */}
                  {editedExtraction.medications.length > 0 && (
                    <div style={{ marginBottom: '12px' }}>
                      <span style={{ ...typography.caption, fontWeight: 700 }}>Extracted Medications ({editedExtraction.medications.length})</span>
                      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '6px', fontSize: '13px' }}>
                        <thead>
                          <tr style={{ borderBottom: `1px solid ${colors.neutral['300']}` }}>
                            <th style={{ textAlign: 'left', padding: '6px 8px' }}>Class</th>
                            <th style={{ textAlign: 'left', padding: '6px 8px' }}>Name</th>
                            <th style={{ textAlign: 'left', padding: '6px 8px' }}>Dose</th>
                            <th style={{ textAlign: 'left', padding: '6px 8px' }}>Freq</th>
                            <th style={{ padding: '6px 8px', width: '40px' }}></th>
                          </tr>
                        </thead>
                        <tbody>
                          {editedExtraction.medications.map((m, i) => (
                            <tr key={i} style={{ borderBottom: `1px solid ${colors.neutral['200']}` }}>
                              <td style={{ padding: '6px 8px' }}>
                                <select value={m.drug_class} onChange={e => {
                                  const updated = [...editedExtraction.medications];
                                  updated[i] = { ...updated[i], drug_class: e.target.value };
                                  setEditedExtraction({ ...editedExtraction, medications: updated });
                                }} style={{ fontSize: '12px', padding: '4px', borderRadius: '4px', border: `1px solid ${colors.neutral['300']}` }}>
                                  {['beta_blocker','ace_inhibitor','arb','antiplatelet','anticoagulant','statin','diuretic','ccb','nitrate','antiarrhythmic','insulin','metformin','sglt2_inhibitor','other'].map(t => <option key={t} value={t}>{t.replace(/_/g,' ')}</option>)}
                                </select>
                              </td>
                              <td style={{ padding: '6px 8px' }}>
                                <input value={m.drug_name} onChange={e => {
                                  const updated = [...editedExtraction.medications];
                                  updated[i] = { ...updated[i], drug_name: e.target.value };
                                  setEditedExtraction({ ...editedExtraction, medications: updated });
                                }} style={{ width: '100%', fontSize: '12px', padding: '4px', borderRadius: '4px', border: `1px solid ${colors.neutral['300']}` }} />
                              </td>
                              <td style={{ padding: '6px 8px' }}>
                                <input value={m.dose || ''} onChange={e => {
                                  const updated = [...editedExtraction.medications];
                                  updated[i] = { ...updated[i], dose: e.target.value };
                                  setEditedExtraction({ ...editedExtraction, medications: updated });
                                }} style={{ width: '80px', fontSize: '12px', padding: '4px', borderRadius: '4px', border: `1px solid ${colors.neutral['300']}` }} />
                              </td>
                              <td style={{ padding: '6px 8px' }}>
                                <select value={m.frequency} onChange={e => {
                                  const updated = [...editedExtraction.medications];
                                  updated[i] = { ...updated[i], frequency: e.target.value };
                                  setEditedExtraction({ ...editedExtraction, medications: updated });
                                }} style={{ fontSize: '12px', padding: '4px', borderRadius: '4px', border: `1px solid ${colors.neutral['300']}` }}>
                                  <option value="daily">Daily</option>
                                  <option value="twice_daily">Twice Daily</option>
                                  <option value="three_times_daily">3x Daily</option>
                                  <option value="as_needed">As Needed</option>
                                  <option value="weekly">Weekly</option>
                                </select>
                              </td>
                              <td style={{ padding: '6px 8px' }}>
                                <button onClick={() => {
                                  const updated = editedExtraction.medications.filter((_, idx) => idx !== i);
                                  setEditedExtraction({ ...editedExtraction, medications: updated });
                                }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: colors.critical.badge, fontSize: '16px' }}>✕</button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {editedExtraction.conditions.length === 0 && editedExtraction.medications.length === 0 && (
                    <p style={{ ...typography.caption, color: colors.neutral['500'], marginBottom: '12px' }}>
                      No conditions or medications were extracted. You can enter them manually using the forms below.
                    </p>
                  )}

                  {/* Confirm / Discard buttons */}
                  <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
                    <button
                      disabled={confirmingExtraction}
                      onClick={async () => {
                        if (!patientId || !extractionResult) return;
                        setConfirmingExtraction(true);
                        try {
                          const profile = await api.confirmDocumentExtraction(Number(patientId), {
                            document_id: extractionResult.document_id,
                            conditions: editedExtraction.conditions,
                            medications: editedExtraction.medications,
                          });
                          setMedicalProfile(profile);
                          setShowExtractionReview(false);
                          setExtractionResult(null);
                          showSnackbar('Document review saved successfully.', 'success');
                        } catch (err: any) {
                          showSnackbar(err?.response?.data?.detail || 'Failed to save', 'error');
                        } finally {
                          setConfirmingExtraction(false);
                        }
                      }}
                      style={{
                        backgroundColor: '#16A34A',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '8px 18px',
                        fontSize: '13px',
                        fontWeight: 600,
                        cursor: confirmingExtraction ? 'not-allowed' : 'pointer',
                        opacity: confirmingExtraction ? 0.6 : 1,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      {confirmingExtraction ? <Loader size={14} /> : <Check size={14} />}
                      {confirmingExtraction ? 'Saving...' : 'Confirm & Save'}
                    </button>
                    <button
                      onClick={() => { setShowExtractionReview(false); setExtractionResult(null); }}
                      style={{
                        backgroundColor: colors.neutral['200'],
                        color: colors.neutral['700'],
                        border: 'none',
                        borderRadius: '6px',
                        padding: '8px 18px',
                        fontSize: '13px',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      Discard
                    </button>
                  </div>
                </div>
              )}

              {/* Cardiac History Section */}
              <div style={{ marginBottom: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ ...typography.body, fontWeight: 700 }}>Cardiac History & Risk Factors</span>
                  <button
                    onClick={() => setShowAddCondition(!showAddCondition)}
                    style={{
                      backgroundColor: colors.primary.default,
                      color: '#fff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '6px 14px',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {showAddCondition ? 'Cancel' : '+ Add Condition'}
                  </button>
                </div>

                {/* Add Condition Form */}
                {showAddCondition && (
                  <div style={{
                    backgroundColor: colors.neutral['50'],
                    border: `1px solid ${colors.neutral['300']}`,
                    borderRadius: '8px',
                    padding: '16px',
                    marginBottom: '12px',
                    display: 'flex',
                    gap: '10px',
                    flexWrap: 'wrap',
                    alignItems: 'flex-end',
                  }}>
                    <div>
                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Condition</label>
                      <select
                        value={newCondition.condition_type}
                        onChange={(e) => setNewCondition({ ...newCondition, condition_type: e.target.value })}
                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
                      >
                        {['prior_mi','cabg','pci_stent','heart_failure','valve_disease','atrial_fibrillation','other_arrhythmia','hypertension','diabetes_type1','diabetes_type2','dyslipidemia','ckd','copd','pad','stroke_tia','smoking','family_cvd','obesity','other'].map(t => (
                          <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Detail</label>
                      <input
                        type="text"
                        placeholder="e.g. NYHA Class II"
                        value={newCondition.condition_detail || ''}
                        onChange={(e) => setNewCondition({ ...newCondition, condition_detail: e.target.value })}
                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px', width: '180px' }}
                      />
                    </div>
                    <div>
                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Status</label>
                      <select
                        value={newCondition.status || 'active'}
                        onChange={(e) => setNewCondition({ ...newCondition, status: e.target.value })}
                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
                      >
                        <option value="active">Active</option>
                        <option value="managed">Managed</option>
                        <option value="resolved">Resolved</option>
                      </select>
                    </div>
                    <button
                      disabled={medProfileSaving}
                      onClick={async () => {
                        if (!patientId) return;
                        setMedProfileSaving(true);
                        try {
                          await api.addPatientCondition(Number(patientId), newCondition);
                          setShowAddCondition(false);
                          setNewCondition({ condition_type: 'prior_mi', condition_detail: '', status: 'active' });
                          // Reload profile
                          const profile = await api.getPatientMedicalProfile(Number(patientId));
                          setMedicalProfile(profile);
                        } catch (e) { console.error('Failed to add condition:', e); }
                        setMedProfileSaving(false);
                      }}
                      style={{
                        backgroundColor: colors.stable.badge,
                        color: '#fff',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '6px 16px',
                        fontSize: '13px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        opacity: medProfileSaving ? 0.6 : 1,
                      }}
                    >
                      {medProfileSaving ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                )}

                {/* Conditions Table */}
                {medicalProfile && medicalProfile.conditions.length > 0 ? (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                      <thead>
                        <tr style={{ borderBottom: `2px solid ${colors.neutral['300']}` }}>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Condition</th>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Detail</th>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Status</th>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {medicalProfile.conditions.map((c) => (
                          <React.Fragment key={c.history_id}>
                            <tr style={{ borderBottom: `1px solid ${colors.neutral['200']}` }}>
                              <td style={{ padding: '8px 12px', fontWeight: 600 }}>
                                {c.condition_type.replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase())}
                              </td>
                              <td style={{ padding: '8px 12px', color: colors.neutral['600'] }}>{c.condition_detail || '—'}</td>
                              <td style={{ padding: '8px 12px' }}>
                                <span style={{
                                  backgroundColor: c.status === 'active' ? colors.critical.background : c.status === 'managed' ? colors.warning.background : colors.stable.background,
                                  color: c.status === 'active' ? colors.critical.text : c.status === 'managed' ? colors.warning.text : colors.stable.text,
                                  fontSize: '11px',
                                  fontWeight: 600,
                                  padding: '2px 8px',
                                  borderRadius: '10px',
                                }}>
                                  {c.status}
                                </span>
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                <button
                                  onClick={() => {
                                    setEditingConditionId(c.history_id);
                                    setEditedCondition({ condition_type: c.condition_type, condition_detail: c.condition_detail || '', status: c.status });
                                  }}
                                  style={{ background: 'none', border: 'none', color: colors.primary.dark, cursor: 'pointer', fontSize: '12px', fontWeight: 600, marginRight: '8px' }}
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={async () => {
                                    if (!patientId || !window.confirm('Delete this condition?')) return;
                                    try {
                                      await api.deletePatientCondition(Number(patientId), c.history_id);
                                      const profile = await api.getPatientMedicalProfile(Number(patientId));
                                      setMedicalProfile(profile);
                                    } catch (e) { console.error('Failed to delete condition:', e); }
                                  }}
                                  style={{ background: 'none', border: 'none', color: colors.critical.badge, cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
                                >
                                  Remove
                                </button>
                              </td>
                            </tr>
                            {editingConditionId === c.history_id && (
                              <tr>
                                <td colSpan={4} style={{ padding: '8px 12px', backgroundColor: colors.neutral['50'], borderBottom: `1px solid ${colors.neutral['300']}` }}>
                                  <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                                    <div>
                                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Condition</label>
                                      <select
                                        value={editedCondition.condition_type || ''}
                                        onChange={(e) => setEditedCondition({ ...editedCondition, condition_type: e.target.value })}
                                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
                                      >
                                        {['prior_mi','cabg','pci_stent','heart_failure','valve_disease','atrial_fibrillation','other_arrhythmia','hypertension','diabetes_type1','diabetes_type2','dyslipidemia','ckd','copd','pad','stroke_tia','smoking','family_cvd','obesity','other'].map(t => (
                                          <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase())}</option>
                                        ))}
                                      </select>
                                    </div>
                                    <div>
                                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Detail</label>
                                      <input
                                        type="text"
                                        value={editedCondition.condition_detail || ''}
                                        onChange={(e) => setEditedCondition({ ...editedCondition, condition_detail: e.target.value })}
                                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px', width: '180px' }}
                                      />
                                    </div>
                                    <div>
                                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Status</label>
                                      <select
                                        value={editedCondition.status || 'active'}
                                        onChange={(e) => setEditedCondition({ ...editedCondition, status: e.target.value })}
                                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
                                      >
                                        <option value="active">Active</option>
                                        <option value="managed">Managed</option>
                                        <option value="resolved">Resolved</option>
                                      </select>
                                    </div>
                                    <button
                                      disabled={medProfileSaving}
                                      onClick={async () => {
                                        if (!patientId || !editingConditionId) return;
                                        setMedProfileSaving(true);
                                        try {
                                          await api.updatePatientCondition(Number(patientId), editingConditionId, editedCondition);
                                          setEditingConditionId(null);
                                          const profile = await api.getPatientMedicalProfile(Number(patientId));
                                          setMedicalProfile(profile);
                                        } catch (e) { console.error('Failed to update condition:', e); }
                                        setMedProfileSaving(false);
                                      }}
                                      style={{ backgroundColor: colors.stable.badge, color: '#fff', border: 'none', borderRadius: '6px', padding: '6px 16px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', opacity: medProfileSaving ? 0.6 : 1 }}
                                    >
                                      {medProfileSaving ? 'Saving...' : 'Save'}
                                    </button>
                                    <button
                                      onClick={() => setEditingConditionId(null)}
                                      style={{ background: 'none', border: `1px solid ${colors.neutral['300']}`, borderRadius: '6px', padding: '6px 14px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', color: colors.neutral['600'] }}
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ ...typography.body, color: colors.neutral['500'], fontStyle: 'italic' }}>
                    No conditions recorded. Click "+ Add Condition" to add cardiac history.
                  </div>
                )}
              </div>

              {/* Medications Section */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ ...typography.body, fontWeight: 700 }}>Medications</span>
                  <button
                    onClick={() => setShowAddMedication(!showAddMedication)}
                    style={{
                      backgroundColor: colors.primary.default,
                      color: '#fff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '6px 14px',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {showAddMedication ? 'Cancel' : '+ Add Medication'}
                  </button>
                </div>

                {/* Add Medication Form */}
                {showAddMedication && (
                  <div style={{
                    backgroundColor: colors.neutral['50'],
                    border: `1px solid ${colors.neutral['300']}`,
                    borderRadius: '8px',
                    padding: '16px',
                    marginBottom: '12px',
                    display: 'flex',
                    gap: '10px',
                    flexWrap: 'wrap',
                    alignItems: 'flex-end',
                  }}>
                    <div>
                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Drug Class</label>
                      <select
                        value={newMedication.drug_class}
                        onChange={(e) => setNewMedication({ ...newMedication, drug_class: e.target.value })}
                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
                      >
                        {['beta_blocker','ace_inhibitor','arb','antiplatelet','anticoagulant','statin','diuretic','ccb','nitrate','antiarrhythmic','insulin','metformin','sglt2_inhibitor','other'].map(t => (
                          <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Drug Name</label>
                      <input
                        type="text"
                        placeholder="e.g. Metoprolol"
                        value={newMedication.drug_name}
                        onChange={(e) => setNewMedication({ ...newMedication, drug_name: e.target.value })}
                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px', width: '150px' }}
                      />
                    </div>
                    <div>
                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Dose</label>
                      <input
                        type="text"
                        placeholder="e.g. 50mg"
                        value={newMedication.dose || ''}
                        onChange={(e) => setNewMedication({ ...newMedication, dose: e.target.value })}
                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px', width: '80px' }}
                      />
                    </div>
                    <div>
                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Frequency</label>
                      <select
                        value={newMedication.frequency || 'daily'}
                        onChange={(e) => setNewMedication({ ...newMedication, frequency: e.target.value })}
                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
                      >
                        <option value="daily">Daily</option>
                        <option value="twice_daily">Twice Daily</option>
                        <option value="three_times_daily">3x Daily</option>
                        <option value="as_needed">As Needed</option>
                        <option value="weekly">Weekly</option>
                      </select>
                    </div>
                    <button
                      disabled={medProfileSaving || !newMedication.drug_name}
                      onClick={async () => {
                        if (!patientId) return;
                        setMedProfileSaving(true);
                        try {
                          await api.addPatientMedication(Number(patientId), newMedication);
                          setShowAddMedication(false);
                          setNewMedication({ drug_class: 'beta_blocker', drug_name: '', dose: '', frequency: 'daily' });
                          const profile = await api.getPatientMedicalProfile(Number(patientId));
                          setMedicalProfile(profile);
                        } catch (e) { console.error('Failed to add medication:', e); }
                        setMedProfileSaving(false);
                      }}
                      style={{
                        backgroundColor: !newMedication.drug_name ? colors.neutral['400'] : colors.stable.badge,
                        color: '#fff',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '6px 16px',
                        fontSize: '13px',
                        fontWeight: 600,
                        cursor: !newMedication.drug_name ? 'not-allowed' : 'pointer',
                        opacity: medProfileSaving ? 0.6 : 1,
                      }}
                    >
                      {medProfileSaving ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                )}

                {/* Medications Table */}
                {medicalProfile && medicalProfile.medications.length > 0 ? (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                      <thead>
                        <tr style={{ borderBottom: `2px solid ${colors.neutral['300']}` }}>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Drug</th>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Class</th>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Dose</th>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Freq</th>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Flags</th>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Status</th>
                          <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.neutral['700'] }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {medicalProfile.medications.map((m) => (
                          <React.Fragment key={m.medication_id}>
                            <tr style={{ borderBottom: `1px solid ${colors.neutral['200']}` }}>
                              <td style={{ padding: '8px 12px', fontWeight: 600 }}>{m.drug_name}</td>
                              <td style={{ padding: '8px 12px', color: colors.neutral['600'] }}>
                                {m.drug_class.replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase())}
                              </td>
                              <td style={{ padding: '8px 12px' }}>{m.dose || '—'}</td>
                              <td style={{ padding: '8px 12px' }}>
                                {(m.frequency || 'daily').replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase())}
                              </td>
                              <td style={{ padding: '8px 12px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                                {m.is_hr_blunting && (
                                  <span style={{ backgroundColor: colors.primary.light, color: colors.primary.dark, fontSize: '10px', fontWeight: 600, padding: '1px 6px', borderRadius: '8px' }}>
                                    HR Blunting
                                  </span>
                                )}
                                {m.is_anticoagulant && (
                                  <span style={{ backgroundColor: colors.warning.background, color: colors.warning.text, fontSize: '10px', fontWeight: 600, padding: '1px 6px', borderRadius: '8px' }}>
                                    Anticoagulant
                                  </span>
                                )}
                                {!m.is_hr_blunting && !m.is_anticoagulant && '—'}
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                <span style={{
                                  backgroundColor: m.status === 'active' ? colors.stable.background : m.status === 'on_hold' ? colors.warning.background : colors.neutral['100'],
                                  color: m.status === 'active' ? colors.stable.text : m.status === 'on_hold' ? colors.warning.text : colors.neutral['600'],
                                  fontSize: '11px',
                                  fontWeight: 600,
                                  padding: '2px 8px',
                                  borderRadius: '10px',
                                }}>
                                  {m.status}
                                </span>
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                <button
                                  onClick={() => {
                                    setEditingMedicationId(m.medication_id);
                                    setEditedMedication({ drug_class: m.drug_class, drug_name: m.drug_name, dose: m.dose || '', frequency: m.frequency || 'daily', status: m.status });
                                  }}
                                  style={{ background: 'none', border: 'none', color: colors.primary.dark, cursor: 'pointer', fontSize: '12px', fontWeight: 600, marginRight: '8px' }}
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={async () => {
                                    if (!patientId || !window.confirm('Delete this medication?')) return;
                                    try {
                                      await api.deletePatientMedication(Number(patientId), m.medication_id);
                                      const profile = await api.getPatientMedicalProfile(Number(patientId));
                                      setMedicalProfile(profile);
                                    } catch (e) { console.error('Failed to delete medication:', e); }
                                  }}
                                  style={{ background: 'none', border: 'none', color: colors.critical.badge, cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
                                >
                                  Remove
                                </button>
                              </td>
                            </tr>
                            {editingMedicationId === m.medication_id && (
                              <tr>
                                <td colSpan={7} style={{ padding: '8px 12px', backgroundColor: colors.neutral['50'], borderBottom: `1px solid ${colors.neutral['300']}` }}>
                                  <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                                    <div>
                                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Drug Class</label>
                                      <select
                                        value={editedMedication.drug_class || ''}
                                        onChange={(e) => setEditedMedication({ ...editedMedication, drug_class: e.target.value })}
                                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
                                      >
                                        {['beta_blocker','ace_inhibitor','arb','antiplatelet','anticoagulant','statin','diuretic','ccb','nitrate','antiarrhythmic','insulin','metformin','sglt2_inhibitor','other'].map(t => (
                                          <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase())}</option>
                                        ))}
                                      </select>
                                    </div>
                                    <div>
                                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Drug Name</label>
                                      <input
                                        type="text"
                                        value={editedMedication.drug_name || ''}
                                        onChange={(e) => setEditedMedication({ ...editedMedication, drug_name: e.target.value })}
                                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px', width: '150px' }}
                                      />
                                    </div>
                                    <div>
                                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Dose</label>
                                      <input
                                        type="text"
                                        value={editedMedication.dose || ''}
                                        onChange={(e) => setEditedMedication({ ...editedMedication, dose: e.target.value })}
                                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px', width: '80px' }}
                                      />
                                    </div>
                                    <div>
                                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Frequency</label>
                                      <select
                                        value={editedMedication.frequency || 'daily'}
                                        onChange={(e) => setEditedMedication({ ...editedMedication, frequency: e.target.value })}
                                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
                                      >
                                        <option value="daily">Daily</option>
                                        <option value="twice_daily">Twice Daily</option>
                                        <option value="three_times_daily">3x Daily</option>
                                        <option value="as_needed">As Needed</option>
                                        <option value="weekly">Weekly</option>
                                      </select>
                                    </div>
                                    <div>
                                      <label style={{ ...typography.caption, display: 'block', marginBottom: '4px' }}>Status</label>
                                      <select
                                        value={editedMedication.status || 'active'}
                                        onChange={(e) => setEditedMedication({ ...editedMedication, status: e.target.value })}
                                        style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.neutral['300']}`, fontSize: '13px' }}
                                      >
                                        <option value="active">Active</option>
                                        <option value="on_hold">On Hold</option>
                                        <option value="discontinued">Discontinued</option>
                                      </select>
                                    </div>
                                    <button
                                      disabled={medProfileSaving || !editedMedication.drug_name}
                                      onClick={async () => {
                                        if (!patientId || !editingMedicationId) return;
                                        setMedProfileSaving(true);
                                        try {
                                          await api.updatePatientMedication(Number(patientId), editingMedicationId, editedMedication);
                                          setEditingMedicationId(null);
                                          const profile = await api.getPatientMedicalProfile(Number(patientId));
                                          setMedicalProfile(profile);
                                        } catch (e) { console.error('Failed to update medication:', e); }
                                        setMedProfileSaving(false);
                                      }}
                                      style={{ backgroundColor: !editedMedication.drug_name ? colors.neutral['400'] : colors.stable.badge, color: '#fff', border: 'none', borderRadius: '6px', padding: '6px 16px', fontSize: '13px', fontWeight: 600, cursor: !editedMedication.drug_name ? 'not-allowed' : 'pointer', opacity: medProfileSaving ? 0.6 : 1 }}
                                    >
                                      {medProfileSaving ? 'Saving...' : 'Save'}
                                    </button>
                                    <button
                                      onClick={() => setEditingMedicationId(null)}
                                      style={{ background: 'none', border: `1px solid ${colors.neutral['300']}`, borderRadius: '6px', padding: '6px 14px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', color: colors.neutral['600'] }}
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ ...typography.body, color: colors.neutral['500'], fontStyle: 'italic' }}>
                    No medications recorded. Click "+ Add Medication" to add.
                  </div>
                )}
              </div>
        </MedicalProfilePanel>

        {/* ================================================================= */}
        {/* Advanced ML: Anomaly Detection Panel                            */}
        {/* ================================================================= */}
        <AdvancedMLPanel
          anomalyData={anomalyData}
          expanded={anomalyExpanded}
          onToggle={() => setAnomalyExpanded((prev) => !prev)}
        >

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
        </AdvancedMLPanel>

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
        {/* Current Activity Plan — Clinician Oversight Card                 */}
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
              <span style={{ ...typography.sectionTitle, margin: 0 }}>Current Activity Plan</span>
            </div>
            {recExpanded ? <ChevronUp size={20} color={colors.neutral['500']} /> : <ChevronDown size={20} color={colors.neutral['500']} />}
          </button>

          {recExpanded && (
            <div style={{ padding: '24px' }}>
              {!recData ? (
                <div style={{ padding: '16px', textAlign: 'center', backgroundColor: colors.neutral['50'], borderRadius: '8px', color: colors.neutral['500'] }}>
                  No activity plan available for this patient.
                </div>
              ) : (() => {
                // ── Computed adherence + tolerance from existing state ──────────
                const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
                const weekSessions = activities.filter(a => a.start_time && new Date(a.start_time) >= sevenDaysAgo);
                const lastSession = activities[0] ?? null;

                // Tolerance
                const hasCautionEvent = weekSessions.some(a => (a.alerts_triggered ?? 0) > 0);
                const hasStoppedEarly = weekSessions.some(a => a.status === 'cancelled' || a.status === 'paused');
                const badFeelings = ['bad', 'very_bad', 'poor'];
                const tolerance: string = hasCautionEvent
                  ? 'Caution event noted'
                  : hasStoppedEarly
                  ? 'Session stopped early'
                  : weekSessions.length === 0
                  ? 'No session data available'
                  : weekSessions.every(a => !badFeelings.includes(a.feeling_after ?? ''))
                  ? 'Well tolerated'
                  : 'Caution event noted';

                const toleranceColor = tolerance === 'Well tolerated'
                  ? colors.stable.text
                  : tolerance === 'No session data available'
                  ? colors.neutral['500']
                  : colors.warning.text;

                // Recovery trend
                const scoredSessions = activities.filter(a => a.recovery_score != null).slice(0, 3);
                let recoveryTrend = 'Insufficient data';
                if (scoredSessions.length >= 2) {
                  const diff = (scoredSessions[0].recovery_score ?? 0) - (scoredSessions[scoredSessions.length - 1].recovery_score ?? 0);
                  recoveryTrend = diff > 5 ? 'Improving ↑' : diff < -5 ? 'Worsening ↓' : 'Stable →';
                }
                const trendColor = recoveryTrend.includes('Improving') ? colors.stable.text
                  : recoveryTrend.includes('Worsening') ? colors.critical.text
                  : colors.neutral['600'];

                // Why this plan reasons
                const alertsThisWeek = alerts.filter(a => a.created_at && new Date(a.created_at) >= sevenDaysAgo);
                const planReasons: string[] = [];
                if (riskAssessment?.risk_level && ['moderate','high','critical'].includes(riskAssessment.risk_level)) {
                  planReasons.push(`Elevated recent risk score (${riskAssessment.risk_level})`);
                }
                const riskDrivers: string[] = (() => {
                  try { return JSON.parse(riskAssessment?.risk_factors_json ?? '[]'); } catch { return []; }
                })();
                riskDrivers.slice(0, 2).forEach(d => {
                  if (d && !d.includes('within expected')) planReasons.push(d);
                });
                if (alertsThisWeek.length > 0) {
                  planReasons.push(`${alertsThisWeek.length} caution alert${alertsThisWeek.length > 1 ? 's' : ''} this week`);
                }
                if ((lastSession?.recovery_score ?? 100) < 60) {
                  planReasons.push('Recovery score below baseline');
                }
                if (planReasons.length === 0) {
                  planReasons.push('Routine plan based on current health status');
                }

                return (
                  <>
                    {/* ── Section 1: Plan Summary ── */}
                    <div style={{
                      padding: '20px',
                      backgroundColor: recData.risk_level === 'high' || recData.risk_level === 'critical'
                        ? colors.critical.background
                        : recData.risk_level === 'moderate'
                        ? colors.warning.background
                        : colors.stable.background,
                      border: `1px solid ${
                        recData.risk_level === 'high' || recData.risk_level === 'critical'
                          ? colors.critical.border
                          : recData.risk_level === 'moderate'
                          ? colors.warning.border
                          : colors.stable.border
                      }`,
                      borderRadius: '10px',
                      marginBottom: '20px',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
                        <Activity size={20} color={colors.neutral['600']} />
                        <span style={{ fontSize: '16px', fontWeight: 700, color: colors.neutral['900'] }}>
                          {recData.recommendation.title}
                        </span>
                      </div>
                      <p style={{ ...typography.body, color: colors.neutral['700'], marginBottom: '16px', lineHeight: '1.6' }}>
                        {recData.recommendation.description}
                      </p>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '10px' }}>
                        {[
                          { label: 'Activity', value: recData.recommendation.suggested_activity },
                          { label: 'Intensity', value: recData.recommendation.intensity_level },
                          { label: 'Duration', value: `${recData.recommendation.duration_minutes} min` },
                          { label: 'Target HR', value: recData.recommendation.target_heart_rate_min && recData.recommendation.target_heart_rate_max
                              ? `${recData.recommendation.target_heart_rate_min}–${recData.recommendation.target_heart_rate_max} BPM`
                              : '—' },
                        ].map(({ label, value }) => (
                          <div key={label} style={{ padding: '10px 12px', backgroundColor: 'rgba(255,255,255,0.7)', borderRadius: '8px', textAlign: 'center' }}>
                            <div style={{ fontSize: '10px', fontWeight: 600, color: colors.neutral['500'], textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: '4px' }}>{label}</div>
                            <div style={{ fontSize: '13px', fontWeight: 700, color: colors.neutral['800'] }}>{value}</div>
                          </div>
                        ))}
                      </div>
                      <div style={{ marginTop: '12px', fontSize: '11px', color: colors.neutral['500'] }}>
                        AI-generated · {recData.recommendation.created_at ? new Date(recData.recommendation.created_at).toLocaleDateString() : '—'}
                      </div>
                    </div>

                    {/* ── Section 2: Why This Plan ── */}
                    <div style={{ marginBottom: '20px' }}>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: colors.neutral['700'], marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Why This Plan</div>
                      <ul style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {planReasons.map((reason, i) => (
                          <li key={i} style={{ fontSize: '13px', color: colors.neutral['700'], lineHeight: '1.5' }}>{reason}</li>
                        ))}
                      </ul>
                    </div>

                    {/* ── Section 3: Adherence & Tolerance ── */}
                    <div style={{ marginBottom: '20px', padding: '16px', backgroundColor: colors.neutral['50'], borderRadius: '10px', border: `1px solid ${colors.neutral['200']}` }}>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: colors.neutral['700'], marginBottom: '14px', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Adherence & Tolerance</div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
                        {/* Last session */}
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 600, color: colors.neutral['500'], textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '4px' }}>Last Session</div>
                          {lastSession ? (
                            <div style={{ fontSize: '13px', color: colors.neutral['800'] }}>
                              {new Date(lastSession.start_time!).toLocaleDateString()} —{' '}
                              <span style={{ fontWeight: 600, color: lastSession.status === 'completed' ? colors.stable.text : colors.warning.text }}>
                                {lastSession.status === 'completed' ? 'Completed ✓' : 'Not completed'}
                              </span>
                            </div>
                          ) : (
                            <div style={{ fontSize: '13px', color: colors.neutral['500'] }}>No sessions recorded yet</div>
                          )}
                        </div>

                        {/* Sessions this week */}
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 600, color: colors.neutral['500'], textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '4px' }}>Sessions This Week</div>
                          <div style={{ fontSize: '13px', fontWeight: 600, color: colors.neutral['800'] }}>{weekSessions.length} session{weekSessions.length !== 1 ? 's' : ''}</div>
                        </div>

                        {/* Tolerance */}
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 600, color: colors.neutral['500'], textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '4px' }}>Tolerance</div>
                          <div style={{ fontSize: '13px', fontWeight: 600, color: toleranceColor }}>{tolerance}</div>
                        </div>

                        {/* Recovery trend */}
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 600, color: colors.neutral['500'], textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '4px' }}>Recovery Trend</div>
                          <div style={{ fontSize: '13px', fontWeight: 600, color: trendColor }}>{recoveryTrend}</div>
                        </div>
                      </div>
                    </div>

                    {/* ── Section 4: Clinician Review ── */}
                    <div style={{ padding: '16px', backgroundColor: colors.neutral['50'], borderRadius: '10px', border: `1px solid ${colors.neutral['200']}` }}>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: colors.neutral['700'], marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Clinician Review</div>
                      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' as const }}>
                        {/* Keep Plan */}
                        <button
                          onClick={() => showSnackbar('Plan noted. No changes made.', 'success')}
                          style={{
                            padding: '8px 18px',
                            backgroundColor: colors.stable.badge,
                            color: colors.neutral.white,
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontWeight: 600,
                            fontSize: '13px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                          }}
                        >
                          <CheckCircle size={15} />
                          Keep Plan
                        </button>

                        {/* Monitor Before Next Session */}
                        <button
                          onClick={async () => {
                            if (!patientId) return;
                            const dateStr = new Date().toLocaleDateString();
                            setNewNoteText(`Clinical review: monitor before next session — ${dateStr}`);
                            // Small delay so state settles, then scroll to notes
                            setTimeout(() => {
                              const el = document.getElementById('clinician-note-textarea');
                              if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.focus(); }
                            }, 100);
                            showSnackbar('Monitoring note prefilled — add details and save.', 'success');
                          }}
                          style={{
                            padding: '8px 18px',
                            backgroundColor: colors.warning.badge,
                            color: colors.neutral.white,
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontWeight: 600,
                            fontSize: '13px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                          }}
                        >
                          <Clock size={15} />
                          Monitor Before Next Session
                        </button>

                        {/* Add Clinician Note */}
                        <button
                          onClick={() => {
                            const el = document.getElementById('clinician-note-textarea');
                            if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.focus(); }
                          }}
                          style={{
                            padding: '8px 18px',
                            backgroundColor: colors.neutral.white,
                            color: colors.neutral['700'],
                            border: `1px solid ${colors.neutral['300']}`,
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontWeight: 600,
                            fontSize: '13px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                          }}
                        >
                          <PenLine size={15} />
                          Add Clinician Note
                        </button>
                      </div>
                    </div>
                  </>
                );
              })()}
            </div>
          )}
        </div>

        <PredictionExplainabilityPanel
          explainData={explainData}
          explainExpanded={explainExpanded}
          explainLoading={explainLoading}
          canRunExplain={Boolean(patient && latestVitals)}
          onToggleExpanded={() => setExplainExpanded(!explainExpanded)}
          onRunExplain={handleExplainPrediction}
        />
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
          <AlertsPanel
            patientId={Number(patientId)}
            alerts={alerts}
            formatTimeAgo={formatTimeAgo}
            onAcknowledgeAlert={handleAcknowledgeAlert}
            onResolveAlert={handleResolveAlert}
          />

          <SessionHistoryPanel activities={activities} />
        </div>
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

export default PatientDetailPage;
