/* MedicalProfilePanel — A collapsible panel showing the patient's medical profile.
   Displays badge counts for active conditions and medications. */

import React from 'react';
// Icons: expand/collapse arrows and a document icon
import { ChevronDown, ChevronUp, FileText } from 'lucide-react';
import { MedicalProfile } from '../../types';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';

// What this panel needs: the medical profile data, expand/collapse state, and child content
interface MedicalProfilePanelProps {
  patientId: number;
  medicalProfile: MedicalProfile | null;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

// The collapsible medical profile panel component
const MedicalProfilePanel: React.FC<MedicalProfilePanelProps> = ({
  medicalProfile,
  expanded,
  onToggle,
  children,
}) => {
  return (
    <div
      style={{
        backgroundColor: colors.neutral.white,
        border: `1px solid ${colors.neutral['300']}`,
        borderRadius: '12px',
        marginBottom: '24px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        overflow: 'hidden',
      }}
    >
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '20px 24px',
          backgroundColor: colors.neutral.white,
          border: 'none',
          cursor: 'pointer',
          borderBottom: expanded ? `1px solid ${colors.neutral['300']}` : 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <FileText size={22} color={colors.primary.default} />
          <span style={{ ...typography.sectionTitle, margin: 0 }}>Medical Profile</span>
          {medicalProfile && medicalProfile.active_condition_count > 0 && (
            <span
              style={{
                backgroundColor: colors.critical.badge,
                color: colors.neutral.white,
                fontSize: '12px',
                fontWeight: 700,
                padding: '2px 10px',
                borderRadius: '12px',
              }}
            >
              {medicalProfile.active_condition_count} conditions
            </span>
          )}
          {medicalProfile && medicalProfile.active_medication_count > 0 && (
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
              {medicalProfile.active_medication_count} medications
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp size={20} color={colors.neutral['500']} />
        ) : (
          <ChevronDown size={20} color={colors.neutral['500']} />
        )}
      </button>

      {expanded && <div style={{ padding: '24px' }}>{children}</div>}
    </div>
  );
};

export default MedicalProfilePanel;
