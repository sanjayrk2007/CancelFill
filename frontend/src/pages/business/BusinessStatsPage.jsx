import { useState, useEffect, useCallback, useMemo } from 'react';
import client from '../../api/client';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import Card from '../../components/ui/Card';
import StatCard from '../../components/ui/StatCard';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import EmptyState from '../../components/ui/EmptyState';
import { SkeletonCard, SkeletonTable } from '../../components/ui/Skeleton';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table';
import { formatCurrency, formatLocalDateTime } from '../../lib/formatters';
import {
  RotateCw,
  AlertCircle,
  Sparkles,
  TrendingUp,
  CheckCircle,
  Clock,
  Calendar,
} from 'lucide-react';

export default function BusinessStatsPage() {
  useDocumentTitle('Business Analytics');

  const [stats, setStats] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const fetchStatsAndBookings = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setIsRefreshing(true);
    }
    setError(null);

    try {
      const [statsRes, bookingsRes] = await Promise.all([
        client.get('/api/v1/business/stats'),
        client.get('/api/v1/business/bookings'),
      ]);
      setStats(statsRes.data);
      setBookings(bookingsRes.data || []);
    } catch (err) {
      console.error('Error fetching business analytics:', err);
      setError(err.response?.data?.detail || 'Failed to load business recovery statistics.');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Poll every 10 seconds without synchronous setState on mount
  useEffect(() => {
    fetchStatsAndBookings(false);

    const intervalId = setInterval(() => {
      fetchStatsAndBookings(false);
    }, 10000);

    return () => clearInterval(intervalId);
  }, [fetchStatsAndBookings]);

  const conversionPercentage = useMemo(() => {
    if (!stats) return '0.0';
    return ((stats.conversion_rate || 0) * 100).toFixed(1);
  }, [stats]);

  const utilizationPercentage = useMemo(() => {
    if (!stats) return '0.0';
    return ((stats.utilization_rate || 0) * 100).toFixed(1);
  }, [stats]);

  // Recent recoveries from existing bookings data
  const recentRecoveries = useMemo(() => {
    return bookings.filter(
      (b) => b.source === 'RECOVERED' || Boolean(b.recovered_from_booking_id)
    );
  }, [bookings]);

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900">
            Business Analytics
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Real-time cancellation recovery impact, revenue preservation, and waitlist conversion.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-zinc-100 text-[11px] text-zinc-600 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>Live polling (10s)</span>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchStatsAndBookings(true)}
            icon={RotateCw}
            isLoading={isRefreshing}
            disabled={loading}
            aria-label="Refresh stats"
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Inline Error State with Retry */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span className="text-xs font-medium">{error}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={() => fetchStatsAndBookings(true)}>
            Retry
          </Button>
        </div>
      )}

      {loading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <SkeletonCard count={4} />
          </div>
          <SkeletonTable rows={4} cols={4} />
        </div>
      ) : stats ? (
        <>
          {/* 1. 4 STAT CARDS (Stripe Dashboard KPI cards) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* KPI 1: Recovered Revenue */}
            <StatCard
              label="Recovered Revenue"
              value={formatCurrency(stats.recovered_revenue)}
              hint="Revenue saved by auto-filling cancellations"
              icon={TrendingUp}
            />

            {/* KPI 2: Recovered Bookings */}
            <StatCard
              label="Recovered Bookings"
              value={stats.recovered_bookings}
              hint="Cancelled slots re-filled from waitlist"
              icon={CheckCircle}
            />

            {/* KPI 3: Conversion Rate */}
            <StatCard
              label="Conversion Rate"
              value={`${conversionPercentage}%`}
              hint={`${stats.offers_accepted} accepted of ${stats.offers_made} offers`}
              icon={Sparkles}
            />

            {/* KPI 4: Slot Utilization */}
            <StatCard
              label="Slot Utilization"
              value={`${utilizationPercentage}%`}
              hint={`${stats.booked_slots} booked of ${stats.total_slots} total slots`}
              icon={Calendar}
            />
          </div>

          {/* 2. ROW OF OFFER COUNTS */}
          <div className="space-y-3">
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Hold Offers Overview
            </h2>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Card className="p-4">
                <span className="text-[11px] font-medium text-zinc-500 uppercase tracking-wider block">
                  Offers Made
                </span>
                <span className="text-xl font-bold text-zinc-900 mt-1 block">
                  {stats.offers_made}
                </span>
              </Card>

              <Card className="p-4">
                <span className="text-[11px] font-medium text-zinc-500 uppercase tracking-wider block">
                  Offers Accepted
                </span>
                <span className="text-xl font-bold text-zinc-900 mt-1 block">
                  {stats.offers_accepted}
                </span>
              </Card>

              <Card className="p-4">
                <span className="text-[11px] font-medium text-zinc-500 uppercase tracking-wider block">
                  Offers Declined
                </span>
                <span className="text-xl font-bold text-zinc-900 mt-1 block">
                  {stats.offers_declined}
                </span>
              </Card>

              <Card className="p-4">
                <span className="text-[11px] font-medium text-zinc-500 uppercase tracking-wider block">
                  Offers Expired
                </span>
                <span className="text-xl font-bold text-zinc-900 mt-1 block">
                  {stats.offers_expired}
                </span>
              </Card>
            </div>
          </div>

          {/* 3. RECENT RECOVERIES LIST (From existing bookings data) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                Recent Cancellation Recoveries
              </h2>
              <span className="text-xs text-zinc-500">
                {recentRecoveries.length} total recovered
              </span>
            </div>

            {recentRecoveries.length === 0 ? (
              <EmptyState
                icon={Clock}
                title="No recoveries recorded yet"
                description="When cancellations occur and are accepted by waitlist candidates, recovered appointments will be listed here."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow hover={false}>
                    <TableHead>Customer</TableHead>
                    <TableHead>Slot ID</TableHead>
                    <TableHead>Recovered Value</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Recovery Source</TableHead>
                    <TableHead align="right">Booked Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentRecoveries.map((recovery) => (
                    <TableRow key={recovery.id}>
                      <TableCell>
                        <span className="font-medium text-zinc-900">
                          {recovery.holder_name || 'Customer'}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-zinc-500 text-xs">
                          {recovery.slot_id}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold text-zinc-900">
                          {formatCurrency(recovery.slot_price)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge status={recovery.status} size="sm" />
                      </TableCell>
                      <TableCell>
                        <Badge status="RECOVERED" size="sm">
                          Recovered from waitlist
                        </Badge>
                      </TableCell>
                      <TableCell align="right">
                        <span className="text-zinc-600 text-xs">
                          {formatLocalDateTime(recovery.booked_at)}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
