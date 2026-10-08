import { Link } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import Button from '../components/ui/Button';
import { Compass, Home } from 'lucide-react';

export default function NotFound() {
  const { role, user } = useAuth();

  const homePath = user
    ? role === 'BUSINESS'
      ? '/business/slots'
      : '/slots'
    : '/login';

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center px-4">
      <div className="w-20 h-20 rounded-3xl bg-slate-900 border border-slate-800 flex items-center justify-center text-indigo-400 mb-6 shadow-2xl shadow-indigo-950/30">
        <Compass className="w-10 h-10 animate-spin-slow" />
      </div>

      <span className="text-xs uppercase font-bold tracking-widest text-indigo-400 mb-2">
        404 Error
      </span>
      <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-3">
        Page Not Found
      </h1>
      <p className="text-sm text-slate-400 max-w-md mb-8 leading-relaxed">
        The page you are looking for does not exist or may have been moved. Return to the dashboard to continue.
      </p>

      <Link to={homePath}>
        <Button variant="primary" icon={Home} size="md">
          Back to Dashboard
        </Button>
      </Link>
    </div>
  );
}
