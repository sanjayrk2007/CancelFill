import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { useToast } from '../context/useToast';
import Button from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Sparkles, Mail, Lock, User, Briefcase, Check } from 'lucide-react';

export default function Register() {
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
      error('Please complete all fields.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await register({ email, password, name, role });
      success(`Welcome to CancelFill, ${user.name}! Account created as ${role}.`);
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
    <div className="max-w-md mx-auto pt-4 sm:pt-8">
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 mb-4 shadow-lg shadow-indigo-600/30 border border-indigo-400/30">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Create an Account
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          Join CancelFill as a Customer or Business Provider
        </p>
      </div>

      <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
        <CardHeader>
          <CardTitle>Registration Details</CardTitle>
          <CardDescription>Select your account type and fill in your details</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Role selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Select Your Role
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setRole('CUSTOMER')}
                  className={`p-3.5 rounded-xl border text-left transition-all relative flex flex-col gap-1 cursor-pointer ${
                    role === 'CUSTOMER'
                      ? 'bg-indigo-600/15 border-indigo-500/80 text-white ring-1 ring-indigo-500/40 shadow-sm'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <User className={`w-4 h-4 ${role === 'CUSTOMER' ? 'text-indigo-400' : 'text-slate-400'}`} />
                    {role === 'CUSTOMER' && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                  </div>
                  <span className="font-semibold text-sm mt-1">Customer</span>
                  <span className="text-[11px] text-slate-400 leading-tight">
                    Browse slots, join waitlists, accept holds
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setRole('BUSINESS')}
                  className={`p-3.5 rounded-xl border text-left transition-all relative flex flex-col gap-1 cursor-pointer ${
                    role === 'BUSINESS'
                      ? 'bg-indigo-600/15 border-indigo-500/80 text-white ring-1 ring-indigo-500/40 shadow-sm'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <Briefcase className={`w-4 h-4 ${role === 'BUSINESS' ? 'text-indigo-400' : 'text-slate-400'}`} />
                    {role === 'BUSINESS' && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                  </div>
                  <span className="font-semibold text-sm mt-1">Business</span>
                  <span className="text-[11px] text-slate-400 leading-tight">
                    Manage capacity, recover revenue, track stats
                  </span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Full Name
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alice Smith"
                  className="w-full bg-slate-950/70 border border-slate-700/80 rounded-xl px-10 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
                />
              </div>
            </div>

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
                  placeholder="name@example.com"
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
                  placeholder="At least 6 characters"
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
              Complete Registration
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="text-center mt-6">
        <p className="text-sm text-slate-400">
          Already have an account?{' '}
          <Link
            to="/login"
            className="text-indigo-400 hover:text-indigo-300 font-semibold underline underline-offset-4 decoration-indigo-500/40 hover:decoration-indigo-400"
          >
            Sign in here
          </Link>
        </p>
      </div>
    </div>
  );
}
