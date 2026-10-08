import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import Spinner from './ui/Spinner';

export default function ProtectedRoute({ children, allowedRoles }) {
  const { user, role, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4">
          <Spinner size="lg" className="text-indigo-400" />
          <p className="text-sm text-slate-400 font-medium animate-pulse">Loading session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    // Redirect user to their respective default home route if accessing unauthorized role area
    const redirectPath = role === 'BUSINESS' ? '/business/slots' : '/slots';
    return <Navigate to={redirectPath} replace />;
  }

  return children;
}
