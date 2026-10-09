import { Link } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import Button from '../components/ui/Button';
import { Compass, Home } from 'lucide-react';

export default function NotFound() {
  useDocumentTitle('Page Not Found');

  const { role, user } = useAuth();

  const homePath = user
    ? role === 'BUSINESS'
      ? '/business/slots'
      : '/slots'
    : '/login';

  return (
    <div className="min-h-[50vh] flex flex-col items-center justify-center text-center px-4">
      <div className="w-12 h-12 rounded-xl bg-zinc-100 flex items-center justify-center text-zinc-600 mb-4">
        <Compass className="w-6 h-6 text-zinc-700" />
      </div>

      <span className="text-[11px] uppercase font-semibold tracking-wider text-zinc-400 mb-1">
        404 error
      </span>
      <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900 mb-2">
        Page not found
      </h1>
      <p className="text-xs text-zinc-500 max-w-sm mb-6 leading-relaxed">
        The page you are looking for does not exist or has been moved. Return to the dashboard to continue.
      </p>

      <Link to={homePath}>
        <Button variant="primary" icon={Home} size="sm">
          Back to Dashboard
        </Button>
      </Link>
    </div>
  );
}
