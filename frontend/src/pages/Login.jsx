import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import useAuthStore from '../stores/auth.store';

export default function Login() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      navigate('/lobby', { replace: true });
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      background: 'var(--color-bg-primary)',
    }}>
      <motion.form
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        style={{
          width: 340,
          padding: 'var(--space-8)',
          background: 'var(--color-bg-card)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)',
          fontFamily: 'var(--font-mono)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-2)' }}>
          <span style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-3xl)' }}>⬡</span>
          <h1 style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-xl)', margin: 'var(--space-2) 0 0' }}>
            LABOURIOUS
          </h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: 0 }}>
            Trading Command Center
          </p>
        </div>

        {error && (
          <div style={{
            color: 'var(--color-text-danger)',
            background: 'rgba(255,68,68,0.08)',
            border: '1px solid var(--color-accent-danger)',
            borderRadius: 'var(--radius-sm)',
            padding: 'var(--space-3)',
            fontSize: 'var(--font-size-sm)',
          }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          <label style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            style={inputStyle}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          <label style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            style={inputStyle}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            background: loading ? 'var(--color-bg-elevated)' : 'var(--color-accent-primary)',
            color: loading ? 'var(--color-text-muted)' : 'var(--color-bg-primary)',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            padding: 'var(--space-3)',
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--font-size-base)',
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            letterSpacing: '0.05em',
          }}
        >
          {loading ? 'LOGGING IN...' : 'LOGIN'}
        </button>
      </motion.form>
    </div>
  );
}

const inputStyle = {
  background: 'var(--color-bg-tertiary)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  padding: 'var(--space-2) var(--space-3)',
  width: '100%',
  boxSizing: 'border-box',
  outline: 'none',
};
