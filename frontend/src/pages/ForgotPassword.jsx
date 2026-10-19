import { useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../api/client';
import { useToast } from '../context/useToast';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import Button from '../components/ui/Button';
import { Mail, MailCheck } from 'lucide-react';

export default function ForgotPassword() {
  useDocumentTitle('Forgot Password');
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const { error } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await client.post('/api/v1/auth/forgot-password', { email: email.trim() });
      setSent(true);
    } catch (err) {
      error(err.response?.data?.detail || 'Could not send the reset link. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-10">
      <div className="bg-white border border-zinc-200 rounded-2xl shadow-sm p-8">
        {sent ? (
          <div className="text-center space-y-3">
            <MailCheck className="w-10 h-10 text-blue-600 mx-auto" />
            <h1 className="text-xl font-bold text-zinc-900">Check your email</h1>
            <p className="text-xs text-zinc-500 leading-relaxed">
              If <strong>{email}</strong> is registered, we&apos;ve sent a link to reset your password. It expires in 30 minutes.
            </p>
            <Link to="/login" className="inline-block text-xs font-medium text-blue-600 hover:underline">
              Back to sign in
            </Link>
          </div>
        ) : (
          <>
            <h1 className="text-xl font-bold tracking-tight text-zinc-900">Reset your password</h1>
            <p className="text-xs text-zinc-500 mt-1 mb-6">
              Enter your account email and we&apos;ll send you a reset link.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="relative">
                <Mail className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  aria-label="Email address"
                  className="w-full bg-white border border-zinc-200 rounded-lg pl-9 pr-3.5 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                />
              </div>
              <Button type="submit" variant="primary" size="md" isLoading={isLoading} className="w-full">
                Send reset link
              </Button>
            </form>
            <div className="mt-5 text-center">
              <Link to="/login" className="text-xs font-medium text-blue-600 hover:underline">
                Back to sign in
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
