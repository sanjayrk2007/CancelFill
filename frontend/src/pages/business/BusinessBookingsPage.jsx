import { useState, useEffect, useCallback, useMemo } from 'react';
import client from '../../api/client';
import { useToast } from '../../context/useToast';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import EmptyState from '../../components/ui/EmptyState';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import { SkeletonTable } from '../../components/ui/Skeleton';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table';
import { formatLocalDateTime, formatCurrency } from '../../lib/formatters';
import { CheckCircle, RotateCw, AlertCircle, Search, X } from 'lucide-react';

export default function BusinessBookingsPage() {
  useDocumentTitle('Business Bookings');

  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'CONFIRMED' | 'RECOVERED' | 'CANCELLED'
  const [searchQuery, setSearchQuery] = useState('');

  // Cancel target state
  const [cancelTarget, setCancelTarget] = useState(null);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelReason, setCancelReason] = useState('');

  const { success, error: toastError } = useToast();

  const fetchBookings = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setLoading(true);
    }
    setError(null);
    try {
      const response = await client.get('/api/v1/business/bookings');
      setBookings(response.data || []);
    } catch (err) {
      console.error('Error fetching business bookings:', err);
      setError(err.response?.data?.detail || 'Failed to load bookings.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBookings(false);
  }, [fetchBookings]);

  const handleConfirmCancel = async () => {
    if (!cancelTarget) return;
    if (!cancelReason.trim()) {
      toastError('Please enter a reason for cancelling.');
      return;
    }
    setIsCancelling(true);
    try {
      const response = await client.post(`/api/v1/bookings/${cancelTarget.id}/cancel`, {
        reason: cancelReason.trim(),
      });
      const msg = response.data?.candidate_selected
        ? 'Booking cancelled. Waitlist candidate has been automatically selected with a temporary hold.'
        : 'Booking cancelled successfully.';
      success(msg);
      setCancelTarget(null);
      setCancelReason('');
      await fetchBookings(true);
    } catch (err) {
      toastError(err.response?.data?.detail || 'Failed to cancel booking.');
    } finally {
      setIsCancelling(false);
    }
  };

  const filteredBookings = useMemo(() => {
    return bookings.filter((b) => {
      const isRecovered = Boolean(b.recovered_from_booking_id || b.source === 'RECOVERED');

      if (filter === 'CONFIRMED' && b.status !== 'CONFIRMED') return false;
      if (filter === 'CANCELLED' && b.status !== 'CANCELLED') return false;
      if (filter === 'RECOVERED' && !isRecovered) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesHolder = b.holder_name?.toLowerCase().includes(q);
        const matchesId = b.id?.toLowerCase().includes(q);
        const matchesSlot = b.slot_id?.toLowerCase().includes(q);
        if (!matchesHolder && !matchesId && !matchesSlot) return false;
      }

      return true;
    });
  }, [bookings, filter, searchQuery]);

  const confirmedCount = useMemo(() => bookings.filter((b) => b.status === 'CONFIRMED').length, [bookings]);
  const recoveredCount = useMemo(
    () => bookings.filter((b) => b.recovered_from_booking_id || b.source === 'RECOVERED').length,
    [bookings]
  );
  const cancelledCount = useMemo(() => bookings.filter((b) => b.status === 'CANCELLED').length, [bookings]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900">
            Client Bookings
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Monitor confirmed appointments and cancellation recovery history.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchBookings(true)}
            icon={RotateCw}
            disabled={loading}
            aria-label="Refresh bookings"
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
          <Button variant="secondary" size="sm" onClick={() => fetchBookings(true)}>
            Retry
          </Button>
        </div>
      )}

      {/* Filter Chips & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 p-1 bg-zinc-100 rounded-lg border border-zinc-200/60 w-fit">
          <button
            type="button"
            onClick={() => setFilter('ALL')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
              filter === 'ALL'
                ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            All ({bookings.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('CONFIRMED')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
              filter === 'CONFIRMED'
                ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            Confirmed ({confirmedCount})
          </button>
          <button
            type="button"
            onClick={() => setFilter('RECOVERED')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
              filter === 'RECOVERED'
                ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            Recovered ({recoveredCount})
          </button>
          <button
            type="button"
            onClick={() => setFilter('CANCELLED')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
              filter === 'CANCELLED'
                ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            Cancelled ({cancelledCount})
          </button>
        </div>

        <div className="relative sm:w-64">
          <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search client or booking ID..."
            className="w-full bg-white border border-zinc-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
            aria-label="Search bookings"
          />
        </div>
      </div>

      {/* Linear-Style Table */}
      {loading ? (
        <SkeletonTable rows={6} cols={6} />
      ) : filteredBookings.length === 0 ? (
        <EmptyState
          icon={CheckCircle}
          title="No bookings found"
          description={
            searchQuery
              ? `No bookings matching "${searchQuery}".`
              : filter !== 'ALL'
              ? `No bookings with filter "${filter.toLowerCase()}".`
              : 'There are currently no customer bookings recorded for your schedule.'
          }
          action={
            searchQuery || filter !== 'ALL' ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setFilter('ALL');
                  setSearchQuery('');
                }}
              >
                Clear filters
              </Button>
            ) : null
          }
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow hover={false}>
              <TableHead>Booking ID</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Recovery Source</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Booked At</TableHead>
              <TableHead align="right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredBookings.map((booking) => {
              const isConfirmed = booking.status === 'CONFIRMED';
              const isRecovered = Boolean(
                booking.recovered_from_booking_id || booking.source === 'RECOVERED'
              );

              return (
                <TableRow key={booking.id}>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-semibold text-zinc-900 font-mono text-xs">
                        #{booking.id}
                      </span>
                      <span className="text-[11px] text-zinc-400 font-mono">
                        Slot: {booking.slot_id}
                      </span>
                    </div>
                  </TableCell>

                  <TableCell>
                    <span className="font-medium text-zinc-900">
                      {booking.holder_name || 'Customer'}
                    </span>
                  </TableCell>

                  <TableCell>
                    <Badge status={booking.status} size="sm" />
                    {booking.status === 'CANCELLED' && booking.cancellation_reason && (
                      <p className="mt-1 text-xs text-zinc-500">Reason: {booking.cancellation_reason}</p>
                    )}
                  </TableCell>

                  <TableCell>
                    {isRecovered ? (
                      <Badge status="RECOVERED" size="sm">
                        Recovered from waitlist
                      </Badge>
                    ) : (
                      <span className="text-zinc-400 text-xs">Direct booking</span>
                    )}
                  </TableCell>

                  <TableCell>
                    <span className="font-semibold text-zinc-900">
                      {formatCurrency(booking.slot_price)}
                    </span>
                  </TableCell>

                  <TableCell>
                    <span className="text-zinc-600 text-xs">
                      {formatLocalDateTime(booking.booked_at)}
                    </span>
                  </TableCell>

                  <TableCell align="right">
                    {isConfirmed && (
                      <Button
                        variant="secondary"
                        size="sm"
                        icon={X}
                        onClick={() => setCancelTarget(booking)}
                      >
                        Cancel
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      {/* CONFIRM DIALOG: CANCEL BOOKING */}
      <ConfirmDialog
        isOpen={Boolean(cancelTarget)}
        title="Cancel Client Booking?"
        description={
          cancelTarget ? (
            <span>
              Are you sure you want to cancel the booking for{' '}
              <strong className="text-zinc-900 font-semibold">
                {cancelTarget.holder_name || 'this client'}
              </strong>
              ? A hold offer will be automatically extended to the next waitlisted customer.
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                maxLength={500}
                rows={3}
                placeholder="Reason for cancellation (required)"
                className="mt-3 block w-full rounded-md border border-zinc-300 p-2 text-sm text-zinc-900"
              />
            </span>
          ) : (
            'Are you sure you want to cancel this booking?'
          )
        }
        confirmText="Cancel Booking"
        cancelText="Keep Booking"
        confirmVariant="danger"
        isLoading={isCancelling}
        onConfirm={handleConfirmCancel}
        onClose={() => {
          if (!isCancelling) {
            setCancelTarget(null);
            setCancelReason('');
          }
        }}
      />
    </div>
  );
}
