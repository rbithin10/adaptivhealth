/* RiskAssessmentPanel — Shows the AI-generated risk assessment for a patient.
   Displays the risk level, contributing factors, and a recommendation.
   Clinicians can trigger a re-computation of the risk score. */

import React from 'react';
// Icons: warning triangle and refresh spinner
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { RecommendationResponse, RiskAssessmentResponse } from '../../types';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';

// What this panel needs: risk data, recommendation, and a handler to recompute
interface RiskAssessmentPanelProps {
  riskAssessment: RiskAssessmentResponse | null;
  recommendation: RecommendationResponse | null;
  riskFactors: string[];
  computingRisk: boolean;
  computeRiskMessage: { type: 'success' | 'error'; text: string } | null;
  onComputeRisk: () => void;
}

// The risk assessment display component
const RiskAssessmentPanel: React.FC<RiskAssessmentPanelProps> = ({
  riskAssessment,
  recommendation,
  riskFactors,
  computingRisk,
  computeRiskMessage,
  onComputeRisk,
}) => {
  return (
    <div style={{ backgroundColor: colors.critical.background, border: `1px solid ${colors.critical.border}`, borderRadius: '12px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <AlertTriangle size={20} color={colors.critical.text} />
          <h3 style={{ ...typography.sectionTitle, color: colors.critical.text, margin: 0 }}>AI Risk Assessment</h3>
        </div>
        <button onClick={onComputeRisk} disabled={computingRisk} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', backgroundColor: colors.primary.default, color: colors.neutral.white, border: 'none', borderRadius: '8px', cursor: computingRisk ? 'not-allowed' : 'pointer', fontWeight: 500, fontSize: '13px', opacity: computingRisk ? 0.7 : 1 }}>
          <RefreshCw size={14} />
          {computingRisk ? 'Computing...' : riskAssessment ? 'Recompute' : 'Run AI Assessment'}
        </button>
      </div>

      {computeRiskMessage && (
        <div style={{ padding: '10px 14px', borderRadius: '8px', marginBottom: '12px', border: `1px solid ${computeRiskMessage.type === 'success' ? colors.stable.border : colors.warning.border}`, backgroundColor: computeRiskMessage.type === 'success' ? colors.stable.background : colors.warning.background, color: computeRiskMessage.type === 'success' ? colors.stable.text : colors.warning.text, fontSize: '13px', fontWeight: 500 }}>
          {computeRiskMessage.text}
        </div>
      )}

      <div style={{ marginBottom: '16px' }}>
        <div style={{ ...typography.body, color: colors.critical.text, marginBottom: '8px' }}>
          <strong>Current Risk: {riskAssessment?.risk_level?.toUpperCase() || 'N/A'} ({(riskAssessment?.risk_score ?? 0).toFixed(2)})</strong>
        </div>
      </div>

      <div style={{ marginBottom: '16px' }}>
        <div style={{ ...typography.body, color: colors.critical.text, fontWeight: 600, marginBottom: '8px' }}>Contributing Factors:</div>
        <ul style={{ margin: 0, paddingLeft: '20px' }}>
          {riskFactors.length === 0 ? (
            <li style={{ ...typography.body, color: colors.critical.text, marginBottom: '4px' }}>No contributing factors available.</li>
          ) : (
            riskFactors.map((factor, idx) => (
              <li key={idx} style={{ ...typography.body, color: colors.critical.text, marginBottom: '4px' }}>
                {factor}
              </li>
            ))
          )}
        </ul>
      </div>

      <div style={{ paddingTop: '16px', borderTop: `1px solid ${colors.critical.border}` }}>
        <div style={{ ...typography.body, color: colors.critical.text, fontWeight: 600 }}>Recommendation:</div>
        <div style={{ ...typography.body, color: colors.critical.text, marginTop: '8px' }}>
          {recommendation?.description || recommendation?.warnings || 'No recommendation available.'}
        </div>
      </div>
    </div>
  );
};

export default RiskAssessmentPanel;
