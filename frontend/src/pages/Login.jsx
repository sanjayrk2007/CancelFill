import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { useToast } from '../context/useToast';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import Button from '../components/ui/Button';
import { Mail, Lock, ArrowRight, CheckCircle2, User, Building2 } from 'lucide-react';

export default function Login() {
  useDocumentTitle('Sign In');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuth();
  const { success, error } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const showDemoLogins = import.meta.env.VITE_SHOW_DEMO_LOGINS === 'true';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      error('Please enter both email and password.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await login(email, password);
      success(`Welcome back, ${user.name || user.email}.`);

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
    <div className="max-w-[1000px] mx-auto py-4 sm:py-8">
      <div className="bg-white border border-zinc-200 rounded-2xl shadow-sm overflow-hidden grid grid-cols-1 md:grid-cols-12 min-h-[580px]">
        {/* Left Brand Panel: 3 steps (Cancellation, Offer, Confirmed) */}
        <div className="md:col-span-5 bg-zinc-900 text-zinc-100 p-8 sm:p-10 flex flex-col justify-between border-b md:border-b-0 md:border-r border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-8">
              <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center text-white text-xs font-bold">
                C
              </div>
              <span className="font-semibold text-white tracking-tight">CancelFill</span>
            </div>

            <h2 className="text-xl sm:text-2xl font-semibold tracking-tight text-white mb-3">
              Automated recovery for appointment schedules
            </h2>
            <p className="text-xs text-zinc-400 leading-relaxed mb-8">
              Transform lost booking revenue into confirmed reservations with algorithmic waitlist re-matching.
            </p>

            {/* 3 Steps */}
            <div className="space-y-6">
              {/* Step 1: Cancellation */}
              <div className="flex items-start gap-3.5">
                <div className="w-6 h-6 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-semibold text-zinc-300 shrink-0 mt-0.5">
                  1
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                    Cancellation
                  </h3>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                    A booked slot opens up unexpectedly when an existing client cancels.
                  </p>
                </div>
              </div>

              {/* Step 2: Offer */}
              <div className="flex items-start gap-3.5">
                <div className="w-6 h-6 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-semibold text-zinc-300 shrink-0 mt-0.5">
                  2
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                    Offer
                  </h3>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                    A temporary hold is immediately dispatched to the next customer in the waitlist queue.
                  </p>
                </div>
              </div>

              {/* Step 3: Confirmed */}
              <div className="flex items-start gap-3.5">
                <div className="w-6 h-6 rounded-full bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-xs font-semibold text-blue-400 shrink-0 mt-0.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                    Confirmed
                  </h3>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                    The waitlist candidate accepts before the timer expires, recovering the opening.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-zinc-800 text-[11px] text-zinc-500">
            Intelligent capacity reservation engine
          </div>
        </div>

        {/* Right Panel: The Login Form */}
        <div className="md:col-span-7 p-8 sm:p-12 flex flex-col justify-center bg-white">
          <div className="max-w-md w-full mx-auto">
            <div className="mb-6">
              <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
                Sign in to your account
              </h1>
              <p className="text-xs text-zinc-500 mt-1">
                Enter your credentials below to access your bookings and schedule.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    className="w-full bg-white border border-zinc-200 rounded-lg pl-9 pr-3.5 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-white border border-zinc-200 rounded-lg pl-9 pr-3.5 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={isLoading}
                className="w-full mt-2"
              >
                <span>Sign In</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </form>

            {/* Demo Accounts: Only when VITE_SHOW_DEMO_LOGINS=true */}
            {showDemoLogins && (
              <div className="mt-8 pt-6 border-t border-zinc-100">
                <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-400 block mb-2.5">
                  Use demo account:
                </span>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => handleQuickLogin('alice@example.com', 'password123')}
                    className="flex flex-col items-start p-2.5 rounded-lg border border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50 transition-colors text-left text-xs cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                  >
                    <div className="flex items-center gap-1 font-semibold text-zinc-900">
                      <User className="w-3 h-3 text-zinc-500 shrink-0" />
                      <span>Alice</span>
                    </div>
                    <span className="text-[10px] text-zinc-500 mt-0.5">Customer</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleQuickLogin('bob@example.com', 'password123')}
                    className="flex flex-col items-start p-2.5 rounded-lg border border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50 transition-colors text-left text-xs cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                  >
                    <div className="flex items-center gap-1 font-semibold text-zinc-900">
                      <User className="w-3 h-3 text-zinc-500 shrink-0" />
                      <span>Bob</span>
                    </div>
                    <span className="text-[10px] text-zinc-500 mt-0.5">Customer</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleQuickLogin('dr_smith@example.com', 'password123')}
                    className="flex flex-col items-start p-2.5 rounded-lg border border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50 transition-colors text-left text-xs cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                  >
                    <div className="flex items-center gap-1 font-semibold text-zinc-900">
                      <Building2 className="w-3 h-3 text-zinc-500 shrink-0" />
                      <span>Dr. Smith</span>
                    </div>
                    <span className="text-[10px] text-zinc-500 mt-0.5">Business</span>
                  </button>
                </div>
              </div>
            )}

            <div className="mt-6 text-center">
              <p className="text-xs text-zinc-500">
                Don&apos;t have an account?{' '}
                <Link
                  to="/register"
                  className="font-medium text-blue-600 hover:text-blue-700 hover:underline"
                >
                  Create an account
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
