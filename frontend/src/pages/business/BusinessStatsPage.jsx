import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import { Card, CardContent } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Spinner from '../../components/ui/Spinner';
import { formatCurrency } from '../../lib/formatters';
import {
  DollarSign,
  CheckCircle2,
  Zap,
  Activity,
  Layers,
  RotateCw,
  AlertCircle,
  Mail,
  CheckCheck,
  XCircle,
  Timer,
  ArrowRight,
} from 'lucide-react';

export default function BusinessStatsPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchStats = useCallback(async (isInitial = false) => {
    if (isInitial) {
      setLoading(true);
    } else {
      setIsRefreshing(true);
    }
    setError(null);

    try {
      const response = await client.get('/api/v1/business/stats');
      setStats(response.data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Error fetching business stats:', err);
      setError(err.response?.data?.detail || 'Failed to load business recovery statistics.');
    } finally {
      if (isInitial) {
        setLoading(false);
      } else {
        setIsRefreshing(false);
      }
    }
  }, []);

  // Poll every 10 seconds
  useEffect(() => {
    fetchStats(true);

    const intervalId = setInterval(() => {
      fetchStats(false);
    }, 10000);

    return () => clearInterval(intervalId);
  }, [fetchStats]);

  const conversionPercentage = stats
    ? ((stats.conversion_rate || 0) * 100).toFixed(1)
    : '0.0';

  const utilizationPercentage = stats
    ? ((stats.utilization_rate || 0) * 100).toFixed(1)
    : '0.0';

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/60">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Business Recovery Dashboard
            </h1>
            <Badge status="BUSINESS">P6 METRICS</Badge>
          </div>
          <p className="text-sm text-slate-400">
            Real-time cancellation recovery impact, revenue preservation, and waitlist offer conversion.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Live 10s auto-refresh indicator */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Auto-refreshing (10s)</span>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchStats(false)}
            icon={RotateCw}
            isLoading={isRefreshing}
            disabled={loading}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <span className="text-sm font-medium">{error}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={() => fetchStats(true)}>
            Retry
          </Button>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="min-h-[350px] flex flex-col items-center justify-center gap-3 p-12 border border-slate-800/80 rounded-2xl bg-slate-900/30">
          <Spinner size="lg" />
          <p className="text-sm text-slate-400">Loading business analytics & recovery KPIs...</p>
        </div>
      ) : stats ? (
        <>
          {/* 1. PRIMARY KPI CARDS */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* KPI 1: Recovered Revenue */}
            <Card className="relative overflow-hidden border-emerald-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950/20 shadow-xl shadow-emerald-950/10 hover:border-emerald-500/40 transition-all">
              <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-emerald-500 to-teal-400" />
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Recovered Revenue
                </span>
                <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-sm">
                  <DollarSign className="w-5 h-5" />
                </div>
              </div>
              <div className="text-3xl font-extrabold text-white tracking-tight">
                {formatCurrency(stats.recovered_revenue)}
              </div>
              <p className="text-xs text-emerald-400/90 mt-2 font-medium">
                Earnings saved by auto-filling cancellations
              </p>
            </Card>

            {/* KPI 2: Recovered Bookings */}
            <Card className="relative overflow-hidden border-indigo-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/20 shadow-xl shadow-indigo-950/10 hover:border-indigo-500/40 transition-all">
              <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-indigo-500 to-violet-400" />
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Recovered Bookings
                </span>
                <div className="w-9 h-9 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-sm">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
              </div>
              <div className="text-3xl font-extrabold text-white tracking-tight">
                {stats.recovered_bookings}
              </div>
              <p className="text-xs text-indigo-300/90 mt-2 font-medium">
                Cancelled slots re-filled from waitlist
              </p>
            </Card>

            {/* KPI 3: Conversion Rate */}
            <Card className="relative overflow-hidden border-purple-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-purple-950/20 shadow-xl shadow-purple-950/10 hover:border-purple-500/40 transition-all">
              <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-purple-500 to-pink-400" />
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Conversion Rate
                </span>
                <div className="w-9 h-9 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-sm">
                  <Zap className="w-5 h-5" />
                </div>
              </div>
              <div className="text-3xl font-extrabold text-white tracking-tight">
                {conversionPercentage}%
              </div>
              <p className="text-xs text-purple-300/90 mt-2 font-medium">
                {stats.offers_accepted} accepted of {stats.offers_made} offers made
              </p>
            </Card>

            {/* KPI 4: Slot Utilization */}
            <Card className="relative overflow-hidden border-sky-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-sky-950/20 shadow-xl shadow-sky-950/10 hover:border-sky-500/40 transition-all">
              <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-sky-500 to-cyan-400" />
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Slot Utilization
                </span>
                <div className="w-9 h-9 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400 shadow-sm">
                  <Activity className="w-5 h-5" />
                </div>
              </div>
              <div className="text-3xl font-extrabold text-white tracking-tight">
                {utilizationPercentage}%
              </div>
              <p className="text-xs text-sky-300/90 mt-2 font-medium">
                {stats.booked_slots} booked of {stats.total_slots} total slots
              </p>
            </Card>
          </div>

          {/* 2. SMALL ROW OF COUNTS (OFFERS FUNNEL) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <span>Hold Offers Summary</span>
              </h3>
              {lastUpdated && (
                <span className="text-[11px] text-slate-500">
                  Last updated: {lastUpdated.toLocaleTimeString()}
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {/* Offers Made */}
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700/60 flex items-center justify-center text-slate-300">
                    <Mail className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-400 block">Offers Made</span>
                    <span className="text-2xl font-bold text-white">{stats.offers_made}</span>
                  </div>
                </div>
              </div>

              {/* Offers Accepted */}
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <CheckCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-400 block">Offers Accepted</span>
                    <span className="text-2xl font-bold text-emerald-300">{stats.offers_accepted}</span>
                  </div>
                </div>
              </div>

              {/* Offers Declined */}
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400">
                    <XCircle className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-400 block">Offers Declined</span>
                    <span className="text-2xl font-bold text-rose-300">{stats.offers_declined}</span>
                  </div>
                </div>
              </div>

              {/* Offers Expired */}
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                    <Timer className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-400 block">Offers Expired</span>
                    <span className="text-2xl font-bold text-amber-300">{stats.offers_expired}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 3. CAPACITY & QUICK ACTIONS SUMMARY */}
          <Card className="border-slate-800 bg-slate-900/80">
            <CardContent className="pt-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 flex-1">
                  <div>
                    <span className="text-xs text-slate-400 uppercase tracking-wider block font-semibold">
                      Total Slots Published
                    </span>
                    <span className="text-xl font-bold text-white mt-1 block">
                      {stats.total_slots}
                    </span>
                  </div>

                  <div>
                    <span className="text-xs text-slate-400 uppercase tracking-wider block font-semibold">
                      Currently Booked
                    </span>
                    <span className="text-xl font-bold text-indigo-300 mt-1 block">
                      {stats.booked_slots}
                    </span>
                  </div>

                  <div>
                    <span className="text-xs text-slate-400 uppercase tracking-wider block font-semibold">
                      Total Cancellations Logged
                    </span>
                    <span className="text-xl font-bold text-rose-300 mt-1 block">
                      {stats.cancellations}
                    </span>
                  </div>
                </div>

                <div className="border-t sm:border-t-0 sm:border-l border-slate-800 pt-4 sm:pt-0 sm:pl-6 flex items-center">
                  <Link to="/business/slots">
                    <Button variant="primary" size="md" icon={Layers}>
                      <span>Manage Slots</span>
                      <ArrowRight className="w-4 h-4 ml-1" />
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
