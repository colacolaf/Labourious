import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import useNotificationsStore from '../stores/notifications.store';

const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};
const pageTransition = { duration: 0.18, ease: 'easeOut' };

const BOOL_FIELDS = [
  { key: 'email_enabled', label: 'Email notifications' },
  { key: 'sms_enabled', label: 'SMS notifications' },
  { key: 'notify_on_trade', label: 'Notify on trade executed' },
  { key: 'notify_on_agent_pause', label: 'Notify on agent pause' },
  { key: 'notify_on_drawdown', label: 'Notify on drawdown warning' },
  { key: 'daily_digest', label: 'Daily digest email' },
];

export default function NotificationsPage() {
  const { preferences, loading, error, saving, fetchPreferences, updatePreferences } =
    useNotificationsStore();
  const [phone, setPhone] = useState('');
  const [authError, setAuthError] = useState(false);

  useEffect(() => {
    fetchPreferences().catch((err) => {
      if (err?.status === 401 || err?.status === 403) setAuthError(true);
    });
  }, [fetchPreferences]);

  useEffect(() => {
    if (preferences?.phone_number != null) {
      setPhone(preferences.phone_number);
    }
  }, [preferences]);

  const handleToggle = (key, value) => {
    updatePreferences({ [key]: value });
  };

  const handlePhoneSave = () => {
    updatePreferences({ phone_number: phone });
  };

  if (authError) {
    return (
      <div style={{ padding: 'var(--space-6)', fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)' }}>
        Please log in to manage notifications.
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-6)', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
        Loading...
      </div>
    );
  }

  if (error && !preferences) {
    return (
      <div style={{ padding: 'var(--space-6)', fontFamily: 'var(--font-mono)', color: 'var(--color-accent-danger)' }}>
        Error: {error}
      </div>
    );
  }

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={pageTransition}
      style={{
        padding: 'var(--space-6)',
        fontFamily: 'var(--font-mono)',
        maxWidth: '520px',
      }}
    >
      <h2 style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-6)' }}>
        Notification Preferences
      </h2>

      {error && (
        <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-4)' }}>
          Error: {error}
        </div>
      )}

      {saving && (
        <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-3)' }}>
          Saving...
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        {BOOL_FIELDS.map(({ key, label }) => (
          <label
            key={key}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3)',
              cursor: 'pointer',
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            <input
              type="checkbox"
              checked={preferences?.[key] ?? false}
              onChange={(e) => handleToggle(key, e.target.checked)}
              style={{ accentColor: 'var(--color-accent-primary)', width: 16, height: 16 }}
            />
            {label}
          </label>
        ))}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
          <label style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
            Phone number (for SMS)
          </label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            onBlur={handlePhoneSave}
            onKeyDown={(e) => e.key === 'Enter' && handlePhoneSave()}
            placeholder="+1234567890"
            style={{
              background: 'var(--color-bg-tertiary)',
              border: '1px solid var(--color-border)',
              borderRadius: '4px',
              color: 'var(--color-text-primary)',
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--font-size-sm)',
              padding: 'var(--space-2) var(--space-3)',
              width: '100%',
              boxSizing: 'border-box',
            }}
          />
        </div>
      </div>
    </motion.div>
  );
}
