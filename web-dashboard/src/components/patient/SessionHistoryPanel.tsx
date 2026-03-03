import React from 'react';
import { ActivitySessionResponse } from '../../types';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';

interface SessionHistoryPanelProps {
  activities: ActivitySessionResponse[];
}

const SessionHistoryPanel: React.FC<SessionHistoryPanelProps> = ({ activities }) => {
  return (
    <div
      style={{
        backgroundColor: colors.neutral.white,
        border: `1px solid ${colors.neutral['300']}`,
        borderRadius: '12px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      }}
    >
      <h3 style={{ ...typography.sectionTitle, marginBottom: '16px' }}>Session History</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {activities.length === 0 ? (
          <div style={{ padding: '12px', backgroundColor: colors.neutral['50'], borderRadius: '8px' }}>
            <div style={{ ...typography.body, fontWeight: 600 }}>No sessions yet</div>
          </div>
        ) : (
          activities.map((session) => (
            <div
              key={session.session_id}
              style={{ padding: '12px', backgroundColor: colors.neutral['50'], borderRadius: '8px' }}
            >
              <div style={{ ...typography.body, fontWeight: 600 }}>
                {new Date(session.start_time).toLocaleDateString()}: {session.duration_minutes ?? '--'}-min{' '}
                {session.activity_type.replaceAll('_', ' ')}
              </div>
              <div style={{ ...typography.caption, color: colors.neutral['500'], marginTop: '4px' }}>
                Avg HR: {session.avg_heart_rate ?? '--'} BPM • Recovery: {session.recovery_time_minutes ?? '--'} min
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default SessionHistoryPanel;
