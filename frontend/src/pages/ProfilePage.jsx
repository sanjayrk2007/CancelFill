import { useState } from 'react';
import { useAuth } from '../context/useAuth';
import { useToast } from '../context/useToast';
import client from '../api/client';
import Avatar from '../components/ui/Avatar';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';

function Field({ label, htmlFor, children }) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1"
      >
        {label}
      </label>
      {children}
    </div>
  );
}

const inputCls =
  'w-full rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors';

export default function ProfilePage() {
  const { user, role, updateUser } = useAuth();
  const { success, error: toastError } = useToast();

  const [nameValue, setNameValue] = useState(user?.name || '');
  const [nameLoading, setNameLoading] = useState(false);

  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError] = useState('');

  const handleNameSave = async (e) => {
    e.preventDefault();
    const trimmed = nameValue.trim();
    if (!trimmed || trimmed.length > 60) return;
    setNameLoading(true);
    try {
      const res = await client.patch('/api/v1/auth/me', { name: trimmed });
      updateUser(res.data);
      success('Name updated.');
    } catch {
      toastError('Failed to update name.');
    } finally {
      setNameLoading(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPwError('');
    if (newPw.length < 8) {
      setPwError('New password must be at least 8 characters.');
      return;
    }
    if (newPw !== confirmPw) {
      setPwError('Passwords do not match.');
      return;
    }
    setPwLoading(true);
    try {
      await client.post('/api/v1/auth/change-password', {
        current_password: currentPw,
        new_password: newPw,
      });
      success('Password changed successfully.');
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to change password.';
      setPwError(msg);
    } finally {
      setPwLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="max-w-lg space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Profile</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Manage your account information and security.
        </p>
      </div>

      {/* Identity card */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
        <div className="flex items-center gap-4">
          <Avatar name={user.name} size="lg" />
          <div>
            <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{user.name}</div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">{user.email}</div>
            <div className="mt-2">
              <Badge status={role} size="sm" />
            </div>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800 grid grid-cols-2 gap-3 text-xs">
          <div>
            <span className="text-zinc-500 dark:text-zinc-400">Account ID</span>
            <div className="font-mono text-zinc-700 dark:text-zinc-300 mt-0.5 truncate">{user.id}</div>
          </div>
          <div>
            <span className="text-zinc-500 dark:text-zinc-400">Member since</span>
            <div className="text-zinc-700 dark:text-zinc-300 mt-0.5">
              {new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
            </div>
          </div>
        </div>
      </div>

      {/* Update name */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-4">Display name</h2>
        <form onSubmit={handleNameSave} className="space-y-4">
          <Field label="Name" htmlFor="profile-name">
            <input
              id="profile-name"
              type="text"
              className={inputCls}
              value={nameValue}
              onChange={(e) => setNameValue(e.target.value)}
              minLength={1}
              maxLength={60}
              required
            />
          </Field>
          <div className="flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={nameLoading || nameValue.trim() === user.name}
            >
              {nameLoading ? 'Saving…' : 'Save name'}
            </Button>
          </div>
        </form>
      </div>

      {/* Change password */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-4">Change password</h2>
        <form onSubmit={handlePasswordChange} className="space-y-4">
          <Field label="Current password" htmlFor="current-pw">
            <input
              id="current-pw"
              type="password"
              className={inputCls}
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              autoComplete="current-password"
              required
            />
          </Field>
          <Field label="New password" htmlFor="new-pw">
            <input
              id="new-pw"
              type="password"
              className={inputCls}
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              minLength={8}
              autoComplete="new-password"
              required
            />
          </Field>
          <Field label="Confirm new password" htmlFor="confirm-pw">
            <input
              id="confirm-pw"
              type="password"
              className={inputCls}
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              minLength={8}
              autoComplete="new-password"
              required
            />
          </Field>
          {pwError && (
            <p className="text-xs text-rose-600 dark:text-rose-400">{pwError}</p>
          )}
          <div className="flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={pwLoading}
            >
              {pwLoading ? 'Updating…' : 'Update password'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
