import { useEffect, useState } from 'react';
import { useAuth } from '../context/useAuth';
import { useToast } from '../context/useToast';
import client from '../api/client';
import Avatar from '../components/ui/Avatar';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { currentSubscription, disablePush, enablePush, getPushConfig, pushSupported } from '../lib/push';

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

  const [bizName, setBizName] = useState(user?.business_name || '');
  const [bizCategory, setBizCategory] = useState(user?.category || 'SALON');
  const [bizPhone, setBizPhone] = useState(user?.contact_phone || '');
  const [bizAddress, setBizAddress] = useState(user?.contact_address || '');
  const [bizLoading, setBizLoading] = useState(false);

  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError] = useState('');

  const [phone, setPhone] = useState(user?.phone || '');
  const [prefs, setPrefs] = useState({
    notify_email: user?.notify_email ?? true,
    notify_sms: user?.notify_sms ?? true,
    notify_push: user?.notify_push ?? true,
  });
  const [prefsLoading, setPrefsLoading] = useState(false);
  const [pushConfig, setPushConfig] = useState({ enabled: false, public_key: null });
  const [pushOn, setPushOn] = useState(false);
  const [pushBusy, setPushBusy] = useState(false);

  useEffect(() => {
    getPushConfig().then(setPushConfig).catch(() => {});
    currentSubscription().then((sub) => setPushOn(Boolean(sub))).catch(() => {});
  }, []);

  useEffect(() => {
    if (user) {
      setNameValue(user.name || '');
      setPhone(user.phone || '');
      setBizName(user.business_name || '');
      setBizCategory(user.category || 'SALON');
      setBizPhone(user.contact_phone || '');
      setBizAddress(user.contact_address || '');
    }
  }, [user]);

  const handlePrefsSave = async (e) => {
    e.preventDefault();
    setPrefsLoading(true);
    try {
      const res = await client.patch('/api/v1/auth/me', { phone: phone.trim(), ...prefs });
      updateUser(res.data);
      success('Notification settings saved.');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail[0]?.msg?.replace('Value error, ', '') : detail;
      toastError(msg || 'Failed to save notification settings.');
    } finally {
      setPrefsLoading(false);
    }
  };

  const handlePushToggle = async () => {
    setPushBusy(true);
    try {
      if (pushOn) {
        await disablePush();
        setPushOn(false);
        success('Push notifications turned off on this device.');
      } else {
        await enablePush(pushConfig.public_key);
        setPushOn(true);
        success('Push notifications enabled on this device.');
      }
    } catch (err) {
      toastError(err.message || 'Could not change push notification settings.');
    } finally {
      setPushBusy(false);
    }
  };

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

  const handleBusinessSave = async (e) => {
    e.preventDefault();
    if (!bizName.trim() || !bizCategory || !bizPhone.trim()) {
      toastError('Business name, category, and contact phone are required.');
      return;
    }
    setBizLoading(true);
    try {
      const res = await client.patch('/api/v1/auth/me', {
        business_name: bizName.trim(),
        category: bizCategory,
        contact_phone: bizPhone.trim(),
        contact_address: bizAddress.trim() || null,
      });
      updateUser(res.data);
      success('Business profile updated.');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail[0]?.msg?.replace('Value error, ', '') : detail;
      toastError(msg || 'Failed to update business profile.');
    } finally {
      setBizLoading(false);
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
      <div>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Profile</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Manage your account information and security.
        </p>
      </div>

      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
        <div className="flex items-center gap-4">
          <Avatar name={user.name} size="lg" />
          <div>
            <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{user.name}</div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">{user.email}</div>
            <div className="mt-2 flex items-center gap-2">
              <Badge status={role} size="sm" />
              {role === 'BUSINESS' && user.category && (
                <Badge status={user.category} size="sm" />
              )}
            </div>
          </div>
        </div>
        {role === 'BUSINESS' && user.business_name && (
          <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800 text-xs">
            <span className="text-zinc-500 dark:text-zinc-400">Business Name</span>
            <div className="font-medium text-zinc-900 dark:text-zinc-100 mt-0.5">{user.business_name}</div>
          </div>
        )}
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

      {role === 'BUSINESS' && (
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-1">Business profile</h2>
          <p className="text-xs text-zinc-500 mb-4">
            Update your business identity, public category, and direct contact details.
          </p>
          <form onSubmit={handleBusinessSave} className="space-y-4">
            <Field label="Business name" htmlFor="biz-name">
              <input
                id="biz-name"
                type="text"
                className={inputCls}
                value={bizName}
                onChange={(e) => setBizName(e.target.value)}
                required
              />
            </Field>
            <Field label="Category" htmlFor="biz-category">
              <select
                id="biz-category"
                className={inputCls}
                value={bizCategory}
                onChange={(e) => setBizCategory(e.target.value)}
                required
              >
                <option value="SALON">Salon</option>
                <option value="TUTOR">Tutor</option>
                <option value="SPORTS">Sports</option>
                <option value="CLINIC">Clinic</option>
                <option value="SERVICE_CENTER">Service Center</option>
                <option value="OTHER">Other</option>
              </select>
            </Field>
            <Field label="Contact phone" htmlFor="biz-phone">
              <input
                id="biz-phone"
                type="tel"
                className={inputCls}
                value={bizPhone}
                onChange={(e) => setBizPhone(e.target.value)}
                required
              />
            </Field>
            <Field label="Contact address (optional)" htmlFor="biz-address">
              <input
                id="biz-address"
                type="text"
                className={inputCls}
                value={bizAddress}
                onChange={(e) => setBizAddress(e.target.value)}
              />
            </Field>
            <div className="flex justify-end">
              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={bizLoading}
              >
                {bizLoading ? 'Saving…' : 'Save business profile'}
              </Button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-1">Notifications</h2>
        <p className="text-xs text-zinc-500 mb-4">
          We always show messages in the app. Pick the extra channels for offers, booking changes and refunds.
        </p>
        <form onSubmit={handlePrefsSave} className="space-y-4">
          <Field label="Mobile number (for SMS)" htmlFor="profile-phone">
            <input
              id="profile-phone"
              type="tel"
              className={inputCls}
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+919876543210"
              autoComplete="tel"
            />
            <p className="mt-1 text-[11px] text-zinc-400">International format, starting with +. Leave blank to remove.</p>
          </Field>
          {[
            ['notify_email', 'Email'],
            ['notify_sms', 'SMS (needs a mobile number)'],
          ].map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-xs text-zinc-700 cursor-pointer">
              <input
                type="checkbox"
                checked={prefs[key]}
                onChange={(e) => setPrefs((p) => ({ ...p, [key]: e.target.checked }))}
                className="rounded border-zinc-300"
              />
              {label}
            </label>
          ))}
          <label className="flex items-center gap-2 text-xs text-zinc-700 cursor-pointer">
            <input
              type="checkbox"
              checked={prefs.notify_push}
              onChange={(e) => setPrefs((p) => ({ ...p, notify_push: e.target.checked }))}
              className="rounded border-zinc-300"
            />
            Push notifications
          </label>
          <div className="flex justify-end">
            <Button type="submit" variant="primary" size="sm" disabled={prefsLoading}>
              {prefsLoading ? 'Saving…' : 'Save notification settings'}
            </Button>
          </div>
        </form>

        <div className="mt-4 pt-4 border-t border-zinc-100 flex items-center justify-between gap-3 text-xs">
          <div>
            <div className="font-medium text-zinc-800">This device</div>
            <div className="text-zinc-500">
              {!pushSupported()
                ? 'This browser does not support push.'
                : !pushConfig.enabled
                  ? 'Push is not configured on the server.'
                  : pushOn
                    ? 'Push is on for this browser.'
                    : 'Push is off for this browser.'}
            </div>
          </div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handlePushToggle}
            disabled={pushBusy || !pushSupported() || !pushConfig.enabled}
          >
            {pushOn ? 'Turn off' : 'Turn on'}
          </Button>
        </div>
      </div>

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
