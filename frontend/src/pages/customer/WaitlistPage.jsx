import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import { useToast } from '../../context/useToast';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Spinner from '../../components/ui/Spinner';
import EmptyState from '../../components/ui/EmptyState';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import { formatLocalDateTime, formatLocalTimeRange, formatCurrency } from '../../lib/formatters';
import {
  Clock,
  DollarSign,
  RotateCw,
  AlertCircle,
  ListOrdered,
} from 'lucide-react';

export default function WaitlistPage() {
  const [waitlistEntries, setWaitlistEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [leaveTarget, setLeaveTarget] = useState(null);
  const [isLeaving, setIsLeaving] = useState(false);

  const { success, error: toastError } = useToast();

  const fetchWaitlist = useCallback(async (isRefresh = false) => {
    if (!isRefresh) setLoading(true);
    setError(null);
    try {
      const response = await client.get('/api/v1/me/waitlist');
      setWaitlistEntries(response.data || []);
    } catch (err) {
      console.error('Error fetching waitlist:', err);
      setError(err.response?.data?.detail || 'Failed to load waitlist entries.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWaitlist();
  }, [fetchWaitlist]);

  const handleConfirmLeave = async () => {
    if (!leaveTarget) return;
    setIsLeaving(true);
    try {
      await client.delete(`/api/v1/waitlist/${leaveTarget.id}`);
      success('Successfully left the waitlist.');
      setLeaveTarget(null);
      await fetchWaitlist(true);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to leave waitlist.';
      toastError(msg);
    } finally {
      setIsLeaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/60">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              My Waitlist Queue
            </h1>
            <Badge status="WAITING">WAITING</Badge>
          </div>
          <p className="text-sm text-slate-400">
            Track your position and queue status for full or upcoming appointment slots.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchWaitlist(true)}
            icon={RotateCw}
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
          <Button variant="secondary" size="sm" onClick={() => fetchWaitlist(false)}>
            Retry
          </Button>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="min-h-[350px] flex flex-col items-center justify-center gap-3 p-12 border border-slate-800/80 rounded-2xl bg-slate-900/30">
          <Spinner size="lg" />
          <p className="text-sm text-slate-400">Loading your waitlist positions...</p>
        </div>
      ) : waitlistEntries.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <EmptyState
              icon={Clock}
              title="No Waitlist Entries"
              description="You are not waiting for any booked slots. Browse available or booked slots to join priority waitlists."
              action={
                <Link to="/slots">
                  <Button variant="primary" size="sm">
                    Browse All Slots
                  </Button>
                </Link>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {waitlistEntries.map((entry) => {
            const isWaiting = entry.status === 'WAITING';

            return (
              <Card
                key={entry.id}
                hover
                className={`flex flex-col justify-between border-slate-800 bg-slate-900/90 ${
                  isWaiting ? 'border-sky-500/20' : 'opacity-80'
                }`}
              >
                <div>
                  <CardHeader className="pb-3 border-b border-slate-800/60">
                    <div className="flex items-start justify-between gap-2">
                      <div className="truncate">
                        <CardTitle className="text-base truncate">
                          {entry.slot?.resource_id || 'Waitlisted Slot'}
                        </CardTitle>
                        <CardDescription className="text-xs text-slate-400 mt-0.5 truncate">
                          Entry: {entry.id}
                        </CardDescription>
                      </div>
                      <Badge status={entry.status} size="sm" />
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-3 pt-1">
                    {/* Queue Position */}
                    <div className="flex items-center gap-2 p-2 rounded-xl bg-sky-950/40 border border-sky-500/30 text-sky-200">
                      <ListOrdered className="w-4 h-4 text-sky-400 shrink-0" />
                      <div className="text-xs font-semibold">
                        {entry.priority_order
                          ? `Queue Position #${entry.priority_order}`
                          : 'Queue Position #1'}
                      </div>
                    </div>

                    {/* Local Start Time & Range */}
                    <div className="flex items-start gap-2.5 text-slate-300">
                      <Clock className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
                      <div className="text-xs">
                        <div className="font-semibold text-slate-200">
                          {formatLocalDateTime(entry.slot?.start_time)}
                        </div>
                        <div className="text-slate-400 text-[11px] mt-0.5">
                          {formatLocalTimeRange(entry.slot?.start_time, entry.slot?.end_time)}
                        </div>
                      </div>
                    </div>

                    {/* Price */}
                    <div className="flex items-center gap-2.5 text-slate-300">
                      <DollarSign className="w-4 h-4 text-emerald-400 shrink-0" />
                      <div className="text-xs font-semibold text-emerald-300">
                        {formatCurrency(entry.slot?.price)}
                      </div>
                    </div>
                  </CardContent>
                </div>

                {/* Footer */}
                <CardFooter className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400">
                    Joined: {formatLocalDateTime(entry.joined_at)}
                  </span>

                  {isWaiting && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-rose-400 hover:text-rose-300 hover:border-rose-500/50"
                      onClick={() => setLeaveTarget(entry)}
                    >
                      Leave waitlist
                    </Button>
                  )}
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}

      {/* Confirmation Dialog: Leave Waitlist */}
      <ConfirmDialog
        isOpen={Boolean(leaveTarget)}
        title="Leave Waitlist Queue?"
        description={
          leaveTarget ? (
            <p>
              Are you sure you want to leave the waitlist for{' '}
              <strong className="text-white">
                {leaveTarget.slot?.resource_id || 'this slot'}
              </strong>
              ? You will forfeit your position in the queue.
            </p>
          ) : (
            'Are you sure you want to leave this waitlist?'
          )
        }
        confirmText="Leave Waitlist"
        cancelText="Stay on Waitlist"
        confirmVariant="danger"
        isLoading={isLeaving}
        onConfirm={handleConfirmLeave}
        onClose={() => !isLeaving && setLeaveTarget(null)}
      />
    </div>
  );
}
