import React from 'react';
import { ArrowDownRight, ArrowUpRight, ChevronDown, ChevronUp, Loader, Minus, Search } from 'lucide-react';
import { ExplainPredictionResponse } from '../../types';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';

interface PredictionExplainabilityPanelProps {
  explainData: ExplainPredictionResponse | null;
  explainExpanded: boolean;
  explainLoading: boolean;
  canRunExplain: boolean;
  onToggleExpanded: () => void;
  onRunExplain: () => Promise<void>;
}

const PredictionExplainabilityPanel: React.FC<PredictionExplainabilityPanelProps> = ({
  explainData,
  explainExpanded,
  explainLoading,
  canRunExplain,
  onToggleExpanded,
  onRunExplain,
}) => {
  return (
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
      <button
        onClick={onToggleExpanded}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '20px 24px',
          backgroundColor: colors.neutral.white,
          border: 'none',
          cursor: 'pointer',
          borderBottom: explainExpanded ? `1px solid ${colors.neutral['300']}` : 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Search size={22} color={colors.primary.default} />
          <span style={{ ...typography.sectionTitle, margin: 0 }}>Prediction Explainability</span>
          {explainData && (
            <span
              style={{
                backgroundColor:
                  explainData.risk_level === 'high' || explainData.risk_level === 'critical'
                    ? colors.critical.background
                    : explainData.risk_level === 'moderate'
                      ? colors.warning.background
                      : colors.stable.background,
                color:
                  explainData.risk_level === 'high' || explainData.risk_level === 'critical'
                    ? colors.critical.text
                    : explainData.risk_level === 'moderate'
                      ? colors.warning.text
                      : colors.stable.text,
                fontSize: '11px',
                fontWeight: 700,
                padding: '2px 10px',
                borderRadius: '12px',
                textTransform: 'capitalize' as const,
              }}
            >
              {explainData.risk_level} — {(explainData.risk_score * 100).toFixed(0)}%
            </span>
          )}
        </div>
        {explainExpanded ? <ChevronUp size={20} color={colors.neutral['500']} /> : <ChevronDown size={20} color={colors.neutral['500']} />}
      </button>

      {explainExpanded && (
        <div style={{ padding: '24px' }}>
          <div style={{ marginBottom: '20px' }}>
            <button
              onClick={onRunExplain}
              disabled={explainLoading || !canRunExplain}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 24px',
                backgroundColor: explainLoading ? colors.neutral['300'] : colors.primary.default,
                color: colors.neutral.white,
                border: 'none',
                borderRadius: '8px',
                cursor: explainLoading || !canRunExplain ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: '14px',
                transition: 'all 0.15s',
              }}
            >
              {explainLoading ? (
                <><Loader size={16} /> Analyzing...</>
              ) : (
                <><Search size={16} /> Explain Risk Using Latest Vitals</>
              )}
            </button>
            <div style={{ ...typography.caption, color: colors.neutral['400'], marginTop: '6px' }}>
              Uses patient’s current vitals and profile to run a prediction with feature importance analysis.
            </div>
          </div>

          {explainData && (
            <>
              <div
                style={{
                  padding: '18px 22px',
                  backgroundColor:
                    explainData.risk_level === 'high' || explainData.risk_level === 'critical'
                      ? colors.critical.background
                      : explainData.risk_level === 'moderate'
                        ? colors.warning.background
                        : colors.stable.background,
                  border: `1px solid ${
                    explainData.risk_level === 'high' || explainData.risk_level === 'critical'
                      ? colors.critical.border
                      : explainData.risk_level === 'moderate'
                        ? colors.warning.border
                        : colors.stable.border
                  }`,
                  borderRadius: '10px',
                  marginBottom: '20px',
                }}
              >
                <p style={{ ...typography.body, lineHeight: '1.7', color: colors.neutral['800'], margin: 0, fontSize: '15px' }}>
                  {explainData.plain_explanation}
                </p>
              </div>

              <div style={{ marginBottom: '8px' }}>
                <div style={{ ...typography.caption, fontWeight: 700, color: colors.neutral['500'], marginBottom: '12px' }}>
                  Top Contributing Features
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {explainData.feature_importance.top_features.map((feature, index) => {
                    const isIncreasing = feature.direction === 'increasing';
                    const isDecreasing = feature.direction === 'decreasing';
                    const barWidth = Math.min(100, Math.abs(feature.contribution) * 500);
                    return (
                      <div
                        key={index}
                        style={{
                          padding: '14px 18px',
                          backgroundColor: colors.neutral['50'],
                          borderRadius: '8px',
                          border: `1px solid ${colors.neutral['200']}`,
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '24px',
                                height: '24px',
                                borderRadius: '50%',
                                backgroundColor:
                                  isIncreasing ? colors.critical.background
                                  : isDecreasing ? colors.stable.background
                                    : colors.neutral['100'],
                                border: `1px solid ${
                                  isIncreasing ? colors.critical.border
                                  : isDecreasing ? colors.stable.border
                                    : colors.neutral['200']
                                }`,
                              }}
                            >
                              {isIncreasing && <ArrowUpRight size={14} color={colors.critical.text} />}
                              {isDecreasing && <ArrowDownRight size={14} color={colors.stable.text} />}
                              {!isIncreasing && !isDecreasing && <Minus size={14} color={colors.neutral['400']} />}
                            </span>
                            <span style={{ fontWeight: 700, fontSize: '14px', color: colors.neutral['800'] }}>
                              {feature.feature.replace(/_/g, ' ').replace(/\b\w/g, character => character.toUpperCase())}
                            </span>
                          </div>
                          <span
                            style={{
                              fontWeight: 700,
                              fontSize: '14px',
                              color: isIncreasing ? colors.critical.text : isDecreasing ? colors.stable.text : colors.neutral['500'],
                            }}
                          >
                            {feature.value}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                          <div style={{ flex: 1, height: '6px', backgroundColor: colors.neutral['100'], borderRadius: '3px', overflow: 'hidden' }}>
                            <div
                              style={{
                                height: '100%',
                                width: `${barWidth}%`,
                                backgroundColor: isIncreasing ? colors.critical.badge : isDecreasing ? colors.stable.badge : colors.neutral['300'],
                                borderRadius: '3px',
                                transition: 'width 0.4s ease',
                              }}
                            />
                          </div>
                          <span style={{ ...typography.caption, color: colors.neutral['500'], minWidth: '50px', textAlign: 'right' }}>
                            {(feature.contribution * 100).toFixed(1)}%
                          </span>
                        </div>

                        <div style={{ ...typography.caption, color: colors.neutral['500'] }}>
                          {feature.explanation}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div style={{ ...typography.caption, color: colors.neutral['400'], marginTop: '12px' }}>
                Method: {explainData.feature_importance.method.replace(/_/g, ' ')} • {explainData.feature_importance.feature_count} features analyzed
              </div>
            </>
          )}

          {!explainData && !explainLoading && (
            <div
              style={{
                padding: '24px',
                textAlign: 'center',
                backgroundColor: colors.neutral['50'],
                borderRadius: '8px',
                color: colors.neutral['500'],
              }}
            >
              Click the button above to run a prediction explanation using this patient’s latest vitals.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PredictionExplainabilityPanel;