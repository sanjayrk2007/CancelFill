import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import client from '../api/client';
import { useToast } from '../context/useToast';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import Button from '../components/ui/Button';
import { Lock } from 'lucide-react';

export default function ResetPassword() {
  useDocumentTitle('Choose a New Password');
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [formError, setFormError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { success } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    if (password.length < 8) return setFormError('Password must be at least 8 characters.');
    if (password !== confirm) return setFormError('Passwords do not match.');
    setIsLoading(true);
    try {
      await client.post('/api/v1/auth/reset-password', { token, new_password: password });
      success('Password updated. Please sign in.');
      navigate('/login', { replace: true });
    } catch (err) {
      const detail = err.response?.data?.detail;
      setFormError(typeof detail === 'string' ? detail : 'Could not reset your password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-10">
      <div className="bg-white border border-zinc-200 rounded-2xl shadow-sm p-8">
        <h1 className="text-xl font-bold tracking-tight text-zinc-900">Choose a new password</h1>
        {!token ? (
          <div className="mt-4 space-y-3">
            <p className="text-xs text-rose-600">This reset link is missing its token.</p>
            <Link to="/forgot-password" className="text-xs font-medium text-blue-600 hover:underline">
              Request a new link
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            {[
              ['New password', password, setPassword],
              ['Confirm new password', confirm, setConfirm],
            ].map(([label, value, setter]) => (
              <div key={label}>
                <label className="block text-xs font-medium text-zinc-700 mb-1.5">{label}</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    autoComplete="new-password"
                    value={value}
                    onChange={(e) => setter(e.target.value)}
                    className="w-full bg-white border border-zinc-200 rounded-lg pl-9 pr-3.5 py-2 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                  />
                </div>
              </div>
            ))}
            {formError && (
              <p className="text-xs text-rose-600">
                {formError}{' '}
                {formError.includes('expired') && (
                  <Link to="/forgot-password" className="font-medium underline">
                    Request a new link
                  </Link>
                )}
              </p>
            )}
            <Button type="submit" variant="primary" size="md" isLoading={isLoading} className="w-full">
              Update password
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
