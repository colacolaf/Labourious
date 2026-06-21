import React, { useState, useEffect } from 'react';
import { Button } from '../Common/Button';
import { Spinner } from '../Common/Spinner';
import useControlRoomStore from '../../stores/controlRoom.store';
import { vaultApi } from '../../utils/api-client';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  marginBottom: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const input = {
  background: 'var(--color-bg-elevated)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  padding: 'var(--space-2) var(--space-3)',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  width: '100%',
  boxSizing: 'border-box',
};

export default function VaultSection() {
  const { saving, changePassword } = useControlRoomStore();

  const [keys, setKeys] = useState([]);
  const [keysLoading, setKeysLoading] = useState(true);
  const [keysError, setKeysError] = useState(null);

  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [pwError, setPwError] = useState(null);
  const [pwSuccess, setPwSuccess] = useState(false);

  useEffect(() => {
    vaultApi.listKeys()
      .then((data) => { setKeys(Array.isArray(data) ? data : []); setKeysLoading(false); })
      .catch((err) => { setKeysError(err.message); setKeysLoading(false); });
  }, []);

  const handleDeleteKey = async (key) => {
    try {
      await vaultApi.deleteKey(key);
      setKeys((ks) => ks.filter((k) => k !== key));
    } catch (err) {
      setKeysError(err.message);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwError(null);
    setPwSuccess(false);
    if (pwForm.new_password !== pwForm.confirm) {
      setPwError('New passwords do not match');
      return;
    }
    if (pwForm.new_password.length < 8) {
      setPwError('New password must be at least 8 characters');
      return;
    }
    try {
      await changePassword({ current_password: pwForm.current_password, new_password: pwForm.new_password });
      setPwSuccess(true);
      setPwForm({ current_password: '', new_password: '', confirm: '' });
    } catch (err) {
      setPwError(err.message);
    }
  };

  return (
    <div>
      {/* Vault keys */}
      <div style={{ marginBottom: 'var(--space-2)', color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', letterSpacing: '0.08em' }}>
        STORED KEYS
      </div>
      <div style={card}>
        {keysLoading ? (
          <Spinner />
        ) : keysError ? (
          <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)' }}>{keysError}</div>
        ) : keys.length === 0 ? (
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No keys in vault</div>
        ) : (
          keys.map((key) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--space-2) 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
              <span style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-sm)' }}>
                🔑 {key}
              </span>
              <Button variant="danger" onClick={() => handleDeleteKey(key)} style={{ padding: '2px 8px', fontSize: '0.65rem' }}>
                Delete
              </Button>
            </div>
          ))
        )}
      </div>

      {/* Change password */}
      <div style={{ marginBottom: 'var(--space-2)', color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', letterSpacing: '0.08em' }}>
        CHANGE VAULT PASSWORD
      </div>
      <form onSubmit={handleChangePassword} style={{ ...card, display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <input
          type="password"
          placeholder="Current password"
          value={pwForm.current_password}
          onChange={(e) => setPwForm((f) => ({ ...f, current_password: e.target.value }))}
          style={input}
          required
          autoComplete="current-password"
        />
        <input
          type="password"
          placeholder="New password (min 8 chars)"
          value={pwForm.new_password}
          onChange={(e) => setPwForm((f) => ({ ...f, new_password: e.target.value }))}
          style={input}
          required
          autoComplete="new-password"
        />
        <input
          type="password"
          placeholder="Confirm new password"
          value={pwForm.confirm}
          onChange={(e) => setPwForm((f) => ({ ...f, confirm: e.target.value }))}
          style={input}
          required
          autoComplete="new-password"
        />
        {pwError && <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)' }}>{pwError}</div>}
        {pwSuccess && <div style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-sm)' }}>✓ Password changed</div>}
        <Button type="submit" disabled={saving}>
          {saving ? 'Changing…' : 'Change Password'}
        </Button>
      </form>
    </div>
  );
}
