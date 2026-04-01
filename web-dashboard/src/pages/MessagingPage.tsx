/*
Messaging page for clinicians.

Shows inbox of patients with unread messages.
Click patient to open chat conversation.
Real-time polling for new messages.
Notifications badge for unread counts.
*/

import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { MessageResponse, InboxSummaryResponse, User } from '../types';
import { colors } from '../theme/colors';
import { typography } from '../theme/typography';
import { Send, ArrowLeft, MessageSquare } from 'lucide-react';
import ClinicianTopBar from '../components/common/ClinicianTopBar';

const MessagingPage: React.FC = () => {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  // List of patient conversations in the inbox sidebar
  const [inbox, setInbox] = useState<InboxSummaryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // The patient conversation currently open
  const [selectedPatient, setSelectedPatient] = useState<InboxSummaryResponse | null>(null);
  // Messages in the currently open conversation
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  // Text the clinician is typing in the message box
  const [newMessage, setNewMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  // Auto-scroll anchor at the bottom of the chat
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // Timer for polling new messages every few seconds
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const selectedPatientRef = useRef<InboxSummaryResponse | null>(null);

  // Scroll the chat window to the newest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // On mount: load current user, inbox, and start polling for new messages
  useEffect(() => {
    const initialize = async () => {
      const user = await loadCurrentUser();
      if (!user) {
        return;
      }
      await loadInbox();

      // Poll every 3 seconds: refresh the open chat, or refresh inbox if no chat is open
      pollingIntervalRef.current = setInterval(() => {
        const selected = selectedPatientRef.current;
        if (selected) {
          loadMessages(selected.patient_id);
        } else {
          loadInbox();
        }
      }, 3000);
    };

    initialize();

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the ref in sync so the polling interval sees the latest selection
  useEffect(() => {
    selectedPatientRef.current = selectedPatient;
  }, [selectedPatient]);

  // Auto-scroll whenever new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Verify the user is a clinician; redirect otherwise
  const loadCurrentUser = async (): Promise<User | null> => {
    try {
      const user = await api.getCurrentUser();
      const role = (user.user_role || '').toLowerCase();
      if (role !== 'clinician') {
        navigate('/dashboard');
        return null;
      }
      setCurrentUser(user);
      return user;
    } catch (e) {
      console.error('Error loading current user:', e);
      navigate('/login');
      return null;
    }
  };

  // Fetch the inbox list (all patient conversations)
  const loadInbox = async () => {
    try {
      setError(null);
      const inboxData = await api.getMessagingInbox();
      setInbox(inboxData || []);
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : 'Failed to load inbox';
      console.error('Error loading inbox:', e);
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  // Fetch the full message thread for a patient and mark unread messages as read
  const loadMessages = async (patientId: number) => {
    try {
      const threadMessages = await api.getMessageThread(patientId, 100);
      setMessages(threadMessages || []);
      
      // Mark unread messages as read
      for (const msg of threadMessages) {
        if (!msg.is_read && msg.receiver_id === currentUser?.user_id) {
          await api.markMessageAsRead(msg.message_id).catch(() => {
            // Silently fail on mark as read
          });
        }
      }
    } catch (e) {
      console.error('Error loading messages:', e);
    }
  };

  // When a clinician clicks a patient name in the inbox
  const handleSelectPatient = async (patient: InboxSummaryResponse) => {
    setSelectedPatient(patient);
    setMessages([]);
    await loadMessages(patient.patient_id);
  };

  // Send the clinician's message to the selected patient
  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedPatient || sendingMessage) return;

    setSendingMessage(true);
    try {
      await api.sendMessage(selectedPatient.patient_id, newMessage.trim());
      setNewMessage('');
      await loadMessages(selectedPatient.patient_id);
    } catch (e) {
      console.error('Error sending message:', e);
      setError('Failed to send message');
    } finally {
      setSendingMessage(false);
    }
  };

  // Go back from the chat view to the inbox list
  const handleBackToInbox = () => {
    setSelectedPatient(null);
    setMessages([]);
    loadInbox();
  };

  // Show timestamps in a human-friendly way (e.g. "5m ago", "2d ago")
  const formatTime = (isoDate: string): string => {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        backgroundColor: colors.neutral['50'],
        fontFamily: '"Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
    >
      <ClinicianTopBar />

      {/* Back to Dashboard */}
      <header
        style={{
          backgroundColor: colors.neutral.white,
          borderBottom: `1px solid ${colors.neutral['300']}`,
          padding: '12px 32px',
        }}
      >
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
            fontSize: '14px',
            fontFamily: 'inherit',
          }}
        >
          <ArrowLeft size={20} />
          Back to Dashboard
        </button>
      </header>

      {/* Main Content Area */}
      <div
        style={{
          display: 'flex',
          flex: 1,
          overflow: 'hidden',
        }}
      >
        {/* Inbox List */}
        <div
          style={{
            width: selectedPatient ? '0%' : '100%',
            maxWidth: selectedPatient ? '0px' : '360px',
            borderRight: `1px solid ${colors.neutral['300']}`,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            transition: 'width 0.3s ease',
          }}
        >
          {/* Inbox Header */}
          <div
            style={{
              padding: '16px',
              borderBottom: `1px solid ${colors.neutral['300']}`,
              backgroundColor: colors.neutral.white,
            }}
          >
            <h2 style={{ ...typography.cardTitle, margin: 0 }}>Inbox</h2>
            <p
              style={{
                ...typography.caption,
                color: colors.neutral['500'],
                margin: '4px 0 0 0',
              }}
            >
              {inbox.length} conversation{inbox.length !== 1 ? 's' : ''}
            </p>
          </div>

        {/* Inbox List */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading ? (
            <div style={{ padding: '24px', textAlign: 'center' }}>
              <p style={typography.body}>Loading inbox...</p>
            </div>
          ) : error ? (
            <div style={{ padding: '24px', textAlign: 'center' }}>
              <p style={{ ...typography.body, color: colors.critical.text }}>
                {error}
              </p>
            </div>
          ) : inbox.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center' }}>
              <MessageSquare size={32} color={colors.neutral['300']} style={{ marginBottom: '8px' }} />
              <p style={{ ...typography.body, color: colors.neutral['500'] }}>
                No messages yet
              </p>
            </div>
          ) : (
            inbox.map((conversation) => (
              <button
                key={conversation.patient_id}
                onClick={() => handleSelectPatient(conversation)}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderBottom: `1px solid ${colors.neutral['200']}`,
                  backgroundColor: colors.neutral.white,
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'background-color 0.2s',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = colors.neutral['50'];
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = colors.neutral.white;
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '4px',
                  }}
                >
                  <div style={{ ...typography.cardTitle, flex: 1, marginRight: '8px' }}>
                    {conversation.patient_name}
                  </div>
                  {conversation.unread_count > 0 && (
                    <div
                      style={{
                        backgroundColor: colors.critical.badge,
                        color: colors.neutral.white,
                        borderRadius: '12px',
                        padding: '2px 8px',
                        fontSize: '12px',
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {conversation.unread_count}
                    </div>
                  )}
                </div>
                <p
                  style={{
                    ...typography.caption,
                    color: colors.neutral['600'],
                    margin: 0,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {conversation.last_message_content}
                </p>
                <p
                  style={{
                    ...typography.caption,
                    color: colors.neutral['500'],
                    margin: '4px 0 0 0',
                  }}
                >
                  {formatTime(conversation.last_message_sent_at)}
                </p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Chat View */}
      {selectedPatient && (
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: colors.neutral.white,
          }}
        >
          {/* Chat Header */}
          <div
            style={{
              padding: '16px',
              borderBottom: `1px solid ${colors.neutral['300']}`,
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            <button
              onClick={handleBackToInbox}
              style={{
                display: 'flex',
                alignItems: 'center',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '4px',
                color: colors.primary.default,
              }}
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <h3 style={{ ...typography.cardTitle, margin: 0 }}>
                {selectedPatient.patient_name}
              </h3>
              <p
                style={{
                  ...typography.caption,
                  color: colors.neutral['500'],
                  margin: '2px 0 0 0',
                }}
              >
                Last message {formatTime(selectedPatient.last_message_sent_at)}
              </p>
            </div>
          </div>

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            {messages.length === 0 ? (
              <div style={{ textAlign: 'center', color: colors.neutral['500'] }}>
                <p style={typography.caption}>No messages yet. Start the conversation!</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.message_id}
                  style={{
                    display: 'flex',
                    justifyContent: msg.sender_id === currentUser?.user_id ? 'flex-end' : 'flex-start',
                  }}
                >
                  <div
                    style={{
                      maxWidth: '70%',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      backgroundColor:
                        msg.sender_id === currentUser?.user_id
                          ? colors.primary.default
                          : colors.neutral['100'],
                      color:
                        msg.sender_id === currentUser?.user_id
                          ? colors.neutral.white
                          : colors.neutral['900'],
                    }}
                  >
                    <p style={{ ...typography.body, margin: 0, wordWrap: 'break-word' }}>
                      {msg.content}
                    </p>
                    <p
                      style={{
                        ...typography.caption,
                        margin: '4px 0 0 0',
                        opacity: 0.7,
                      }}
                    >
                      {formatTime(msg.sent_at)}
                    </p>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Message Input */}
          <div
            style={{
              padding: '16px',
              borderTop: `1px solid ${colors.neutral['300']}`,
              display: 'flex',
              gap: '8px',
            }}
          >
            <input
              type="text"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !sendingMessage) {
                  handleSendMessage();
                }
              }}
              placeholder="Type a message..."
              style={{
                flex: 1,
                padding: '10px 12px',
                borderRadius: '6px',
                border: `1px solid ${colors.neutral['300']}`,
                fontFamily: 'inherit',
                fontSize: '14px',
              }}
              disabled={sendingMessage}
            />
            <button
              onClick={handleSendMessage}
              disabled={!newMessage.trim() || sendingMessage}
              style={{
                padding: '10px 16px',
                borderRadius: '6px',
                backgroundColor: colors.primary.default,
                color: colors.neutral.white,
                border: 'none',
                cursor: sendingMessage ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                opacity: sendingMessage ? 0.6 : 1,
                fontWeight: 600,
              }}
            >
              <Send size={16} />
              Send
            </button>
          </div>
        </div>
      )}
      </div>
    </div>
  );
};

export default MessagingPage;
