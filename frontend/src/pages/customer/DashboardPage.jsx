import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';
import client from '../../api/client';
import StatCard from '../../components/ui/StatCard';
import Skeleton from '../../components/ui/Skeleton';
import {
  CalendarDays,
  CheckCircle,
  RefreshCcw,
  Clock,
  Sparkles,
  TrendingUp,
  XCircle,
  ArrowRight,
} from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isCurrent = true;
    setLoading(true);
    client
      .get('/api/v1/me/stats')
      .then((res) => {
        if (!isCurrent) return;
        setStats(res.data);
      })
      .catch(() => {
        if (!isCurrent) return;
        setError('Failed to load stats.');
      })
      .finally(() => {
        if (!isCurrent) return;
        setLoading(false);
      });
    return () => { isCurrent = false; };
  }, []);

  const acceptancePct = stats
    ? stats.offers_received > 0
      ? `${Math.round(stats.acceptance_rate * 100)}%`
      : '—'
    : null;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          Welcome back{user?.name ? `, ${user.name.split(' ')[0]}` : ''}
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Here is a summary of your activity on CancelFill.
        </p>
      </div>

      {/* Primary KPI row */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 space-y-2">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-7 w-12" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="text-sm text-rose-600 dark:text-rose-400">{error}</div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard
              label="Total bookings"
              value={stats.total_bookings}
              icon={<CalendarDays className="w-4 h-4" />}
            />
            <StatCard
              label="Upcoming"
              value={stats.upcoming_bookings}
              icon={<Clock className="w-4 h-4" />}
            />
            <StatCard
              label="Recovered"
              value={stats.recovered_bookings}
              icon={<RefreshCcw className="w-4 h-4" />}
            />
            <StatCard
              label="Cancelled"
              value={stats.cancelled_bookings}
              icon={<XCircle className="w-4 h-4" />}
            />
          </div>

          {/* Offers section */}
          <div>
            <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">Offer activity</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard
                label="Offers received"
                value={stats.offers_received}
                icon={<Sparkles className="w-4 h-4" />}
              />
              <StatCard
                label="Accepted"
                value={stats.offers_accepted}
                icon={<CheckCircle className="w-4 h-4" />}
              />
              <StatCard
                label="Declined"
                value={stats.offers_declined}
                icon={<XCircle className="w-4 h-4" />}
              />
              <StatCard
                label="Acceptance rate"
                value={acceptancePct}
                icon={<TrendingUp className="w-4 h-4" />}
              />
            </div>
          </div>

          {/* Waitlist */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
                  <Clock className="w-4 h-4 text-zinc-600 dark:text-zinc-400" />
                </div>
                <div>
                  <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Active waitlist entries</div>
                  <div className="text-xs text-zinc-500 dark:text-zinc-400">Slots you are currently waiting on</div>
                </div>
              </div>
              <span className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">{stats.active_waitlist_entries}</span>
            </div>
          </div>
        </>
      )}

      {/* Quick links */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">Quick access</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { to: '/slots', label: 'Browse available slots', desc: 'Find and book open slots', icon: CalendarDays },
            { to: '/offers', label: 'View my offers', desc: 'Respond to pending offers before they expire', icon: Sparkles },
            { to: '/bookings', label: 'My bookings', desc: 'See all your confirmed and past bookings', icon: CheckCircle },
            { to: '/waitlist', label: 'My waitlist', desc: 'Manage the slots you are waiting on', icon: Clock },
          ].map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="group flex items-center justify-between bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 hover:border-zinc-300 dark:hover:border-zinc-700 hover:shadow-sm transition-all"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center group-hover:bg-blue-50 dark:group-hover:bg-blue-950/50 transition-colors">
                  <link.icon className="w-4 h-4 text-zinc-500 dark:text-zinc-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
                </div>
                <div>
                  <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{link.label}</div>
                  <div className="text-xs text-zinc-500 dark:text-zinc-400">{link.desc}</div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-zinc-300 dark:text-zinc-600 group-hover:text-zinc-500 dark:group-hover:text-zinc-400 transition-colors" />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
