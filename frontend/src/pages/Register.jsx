import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { useToast } from '../context/useToast';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import Button from '../components/ui/Button';
import { Mail, Lock, User, Building2, CheckCircle2, ArrowRight } from 'lucide-react';

export default function Register() {
  useDocumentTitle('Create Account');

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('CUSTOMER');
  const [isLoading, setIsLoading] = useState(false);

  const { register } = useAuth();
  const { success, error } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !email || !password) {
      error('Please complete all required fields.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await register({ email, password, name, role });
      success(`Welcome to CancelFill, ${user.name}. Account created as ${role}.`);
      if (role === 'BUSINESS') {
        navigate('/business/slots', { replace: true });
      } else {
        navigate('/slots', { replace: true });
      }
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        'Registration failed. This email may already be registered.';
      error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-[1000px] mx-auto py-4 sm:py-8">
      <div className="bg-white border border-zinc-200 rounded-2xl shadow-sm overflow-hidden grid grid-cols-1 md:grid-cols-12 min-h-[580px]">
        {/* Left Brand Panel: 3 steps */}
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
              Join CancelFill to manage priority waitlists, fill unexpected openings, and preserve revenue.
            </p>

            <div className="space-y-6">
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

        {/* Right Panel: Registration Form */}
        <div className="md:col-span-7 p-8 sm:p-12 flex flex-col justify-center bg-white">
          <div className="max-w-md w-full mx-auto">
            <div className="mb-6">
              <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
                Create an account
              </h1>
              <p className="text-xs text-zinc-500 mt-1">
                Choose your account type and fill in your details to get started.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Role selection tabs */}
              <div>
                <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                  Account Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setRole('CUSTOMER')}
                    className={`p-3 rounded-lg border text-left transition-all cursor-pointer flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 ${
                      role === 'CUSTOMER'
                        ? 'border-blue-600 bg-blue-50/40 text-blue-900 ring-1 ring-blue-600'
                        : 'border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50'
                    }`}
                  >
                    <User className={`w-4 h-4 ${role === 'CUSTOMER' ? 'text-blue-600' : 'text-zinc-500'}`} />
                    <div>
                      <div className="text-xs font-semibold">Customer</div>
                      <div className="text-[10px] text-zinc-500">Book & waitlist slots</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setRole('BUSINESS')}
                    className={`p-3 rounded-lg border text-left transition-all cursor-pointer flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 ${
                      role === 'BUSINESS'
                        ? 'border-blue-600 bg-blue-50/40 text-blue-900 ring-1 ring-blue-600'
                        : 'border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50'
                    }`}
                  >
                    <Building2 className={`w-4 h-4 ${role === 'BUSINESS' ? 'text-blue-600' : 'text-zinc-500'}`} />
                    <div>
                      <div className="text-xs font-semibold">Business</div>
                      <div className="text-[10px] text-zinc-500">Manage slots & revenue</div>
                    </div>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                  Full Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Alice Smith"
                    className="w-full bg-white border border-zinc-200 rounded-lg pl-9 pr-3.5 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                  Email Address
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
                    placeholder="At least 6 characters"
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
                <span>Complete Registration</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-xs text-zinc-500">
                Already have an account?{' '}
                <Link
                  to="/login"
                  className="font-medium text-blue-600 hover:text-blue-700 hover:underline"
                >
                  Sign in here
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
