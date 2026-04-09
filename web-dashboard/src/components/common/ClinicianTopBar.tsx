/* ClinicianTopBar — The navigation bar at the top of the page for clinicians.
   Shows the app logo, the clinician's name, a Messages button, and Logout. */

// React and hooks for tracking state and side effects
import React, { useEffect, useState } from 'react';
// Navigation helpers from React Router
import { useLocation, useNavigate } from 'react-router-dom';
import { Heart, LogOut, MessageSquare } from 'lucide-react';
import { api } from '../../services/api';
import { User } from '../../types';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';

// The top navigation bar component
const ClinicianTopBar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  // Keep track of who's logged in and how many unread messages they have
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [unreadMessageCount, setUnreadMessageCount] = useState(0);

  // When the page loads, fetch the current user and their unread message count
  // Also re-check every 5 seconds so the badge stays up to date
  useEffect(() => {
    let isMounted = true;

    const loadTopBarData = async () => {
      try {
        const user = await api.getCurrentUser();
        if (!isMounted) return;
        setCurrentUser(user);

        const role = (user.user_role || '').toLowerCase();
        if (role === 'clinician') {
          const inbox = await api.getMessagingInbox();
          if (!isMounted) return;
          const totalUnread = inbox.reduce((sum, conv) => sum + conv.unread_count, 0);
          setUnreadMessageCount(totalUnread);
        }
      } catch (e) {
        console.warn('Could not load top bar data:', e);
      }
    };

    loadTopBarData();
    const interval = setInterval(loadTopBarData, 5000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Log out: tell the server, then go to the login page
  const handleLogout = async () => {
    // This clears the HttpOnly session cookie on the backend and local user cache in the client.
    await api.logout();
    navigate('/login');
  };

  // Check if we're already on the messages page (to disable the Messages button)
  const isMessagesPage = location.pathname.startsWith('/messages');

  // Render the top bar with logo, user name, Messages button, and Logout
  return (
    <header
      style={{
        backgroundColor: colors.neutral.white,
        borderBottom: `1px solid ${colors.neutral['300']}`,
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 32px',
          maxWidth: '1440px',
          margin: '0 auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Heart size={28} color={colors.primary.default} fill={colors.primary.default} />
          <h1
            style={{
              margin: 0,
              fontSize: '20px',
              fontWeight: 700,
              color: colors.neutral['900'],
            }}
          >
            Adaptiv Health
          </h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <span style={{ ...typography.body, color: colors.neutral['700'] }}>
            {currentUser?.full_name || 'Clinician'}
          </span>

          <button
            onClick={() => navigate('/messages')}
            disabled={isMessagesPage}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: '6px',
              border: `1px solid ${colors.neutral['300']}`,
              backgroundColor: colors.neutral.white,
              cursor: isMessagesPage ? 'default' : 'pointer',
              color: unreadMessageCount > 0 ? colors.critical.badge : colors.neutral['700'],
              fontWeight: unreadMessageCount > 0 ? 600 : 500,
              opacity: isMessagesPage ? 0.75 : 1,
              transition: 'all 0.2s',
              position: 'relative',
            }}
          >
            <MessageSquare size={18} />
            Messages
            {unreadMessageCount > 0 && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  minWidth: '20px',
                  height: '20px',
                  backgroundColor: colors.critical.badge,
                  color: colors.neutral.white,
                  borderRadius: '50%',
                  fontSize: '12px',
                  fontWeight: 700,
                  marginLeft: '4px',
                }}
              >
                {unreadMessageCount}
              </span>
            )}
          </button>

          <button
            onClick={handleLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: '6px',
              border: `1px solid ${colors.neutral['300']}`,
              backgroundColor: colors.neutral.white,
              cursor: 'pointer',
              color: colors.neutral['700'],
              fontWeight: 500,
              transition: 'all 0.2s',
            }}
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </div>
    </header>
  );
};

export default ClinicianTopBar;