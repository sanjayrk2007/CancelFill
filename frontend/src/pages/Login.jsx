import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { useToast } from '../context/useToast';
import Button from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Sparkles, Mail, Lock, Briefcase, User } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuth();
  const { success, error } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      error('Please fill in both email and password.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await login(email, password);
      success(`Welcome back, ${user.name || user.email}!`);

      const destination =
        location.state?.from?.pathname ||
        (user.role === 'BUSINESS' ? '/business/slots' : '/slots');
      navigate(destination, { replace: true });
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        'Failed to log in. Please check your credentials and try again.';
      error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
  };

  return (
    <div className="max-w-md mx-auto pt-6 sm:pt-12">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 mb-4 shadow-lg shadow-indigo-600/30 border border-indigo-400/30">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Sign In to CancelFill
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          Automated slot allocation and intelligent cancellation recovery
        </p>
      </div>

      <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
        <CardHeader>
          <CardTitle>Account Credentials</CardTitle>
          <CardDescription>Enter your email and password to access your portal</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="w-full bg-slate-950/70 border border-slate-700/80 rounded-xl px-10 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-950/70 border border-slate-700/80 rounded-xl px-10 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              className="w-full mt-2"
            >
              Sign In
            </Button>
          </form>

          {/* Quick Demo Logins for Fast Review Testing */}
          <div className="mt-6 pt-5 border-t border-slate-800/80">
            <span className="text-xs font-medium text-slate-400 block mb-2 text-center">
              Quick Test Accounts (Click to Fill):
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('dr_smith@example.com', 'password123')}
                className="flex items-center gap-1.5 p-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-xs text-slate-200 transition-colors text-left"
              >
                <Briefcase className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <div className="truncate">
                  <div className="font-semibold truncate">Dr. Smith</div>
                  <div className="text-[10px] text-slate-400">Business</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('alice@example.com', 'password123')}
                className="flex items-center gap-1.5 p-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-xs text-slate-200 transition-colors text-left"
              >
                <User className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <div className="truncate">
                  <div className="font-semibold truncate">Alice</div>
                  <div className="text-[10px] text-slate-400">Customer</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('bob@example.com', 'password123')}
                className="flex items-center gap-1.5 p-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-xs text-slate-200 transition-colors text-left"
              >
                <User className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                <div className="truncate">
                  <div className="font-semibold truncate">Bob</div>
                  <div className="text-[10px] text-slate-400">Customer</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('charlie@example.com', 'password123')}
                className="flex items-center gap-1.5 p-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-xs text-slate-200 transition-colors text-left"
              >
                <User className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                <div className="truncate">
                  <div className="font-semibold truncate">Charlie</div>
                  <div className="text-[10px] text-slate-400">Customer</div>
                </div>
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="text-center mt-6">
        <p className="text-sm text-slate-400">
          Don&apos;t have an account?{' '}
          <Link
            to="/register"
            className="text-indigo-400 hover:text-indigo-300 font-semibold underline underline-offset-4 decoration-indigo-500/40 hover:decoration-indigo-400"
          >
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
