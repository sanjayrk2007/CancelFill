import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import { useToast } from '../../context/useToast';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import Card from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import EmptyState from '../../components/ui/EmptyState';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import { SkeletonCard } from '../../components/ui/Skeleton';
import { formatLocalDateTime, formatLocalTimeRange, formatCurrency } from '../../lib/formatters';
import {
  Clock,
  RotateCw,
  AlertCircle,
  Info,
  CalendarDays,
  X,
} from 'lucide-react';

export default function WaitlistPage() {
  useDocumentTitle('My Waitlist');

  const [waitlistEntries, setWaitlistEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [leaveTarget, setLeaveTarget] = useState(null);
  const [isLeaving, setIsLeaving] = useState(false);

  const { success, error: toastError } = useToast();

  const fetchWaitlist = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setLoading(true);
    }
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
    fetchWaitlist(false);
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900">
            My Waitlist
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Track your queue position for appointment slots.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchWaitlist(true)}
            icon={RotateCw}
            disabled={loading}
            aria-label="Refresh waitlist"
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* One-line note on how offers arrive */}
      <div className="flex items-center gap-2.5 p-3 rounded-lg bg-blue-50/60 border border-blue-200/60 text-xs text-blue-900">
        <Info className="w-4 h-4 text-blue-600 shrink-0" />
        <span>
          When an appointment cancels, a temporary hold offer is automatically dispatched to the next person in line.
        </span>
      </div>

      {/* Inline Error State with Retry */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span className="text-xs font-medium">{error}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={() => fetchWaitlist(true)}>
            Retry
          </Button>
        </div>
      )}

      {/* Main Content: Rows with large #2 position */}
      {loading ? (
        <SkeletonCard count={3} />
      ) : waitlistEntries.length === 0 ? (
        <EmptyState
          icon={Clock}
          title="No waitlist entries"
          description="You are not waiting for any booked slots. Browse schedule openings to join priority waitlists."
          action={
            <Link to="/slots">
              <Button variant="primary" size="sm">
                Browse slots
              </Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
          {waitlistEntries.map((entry) => {
            const isWaiting = entry.status === 'WAITING';
            const position = entry.priority_order || 1;

            return (
              <Card
                key={entry.id}
                hover
                className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-5"
              >
                {/* Left: Large Position number + slot details */}
                <div className="flex items-start sm:items-center gap-4">
                  {/* Large Position display: e.g. #2 */}
                  <div className="flex flex-col items-center justify-center w-14 h-14 rounded-xl bg-zinc-100 border border-zinc-200 shrink-0">
                    <span className="text-xs uppercase font-medium text-zinc-500 leading-none">
                      Queue
                    </span>
                    <span className="text-2xl font-bold text-zinc-900 tracking-tight leading-none mt-1">
                      #{position}
                    </span>
                  </div>

                  {/* Slot Details */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-zinc-900">
                        {entry.slot?.resource_id || 'Appointment Opening'}
                      </h3>
                      <Badge status={entry.status} size="sm" />
                    </div>

                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-500">
                      <span className="flex items-center gap-1">
                        <CalendarDays className="w-3.5 h-3.5 text-zinc-400" />
                        <span>{formatLocalDateTime(entry.slot?.start_time)}</span>
                      </span>
                      <span>•</span>
                      <span>{formatLocalTimeRange(entry.slot?.start_time, entry.slot?.end_time)}</span>
                      <span>•</span>
                      <span className="font-semibold text-zinc-900">{formatCurrency(entry.slot?.price)}</span>
                    </div>

                    <div className="text-[11px] text-zinc-400 pt-0.5">
                      Joined {formatLocalDateTime(entry.joined_at)}
                    </div>
                  </div>
                </div>

                {/* Right: Leave Button */}
                <div className="flex items-center justify-end sm:shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-zinc-100">
                  {isWaiting && (
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={X}
                      onClick={() => setLeaveTarget(entry)}
                    >
                      Leave waitlist
                    </Button>
                  )}
                </div>
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
            <span>
              Are you sure you want to leave the waitlist for{' '}
              <strong className="text-zinc-900 font-semibold">
                {leaveTarget.slot?.resource_id || 'this slot'}
              </strong>
              ? You will forfeit your place in line.
            </span>
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
