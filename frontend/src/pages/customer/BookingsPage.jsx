import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import { useToast } from '../../context/useToast';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import Card from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import EmptyState from '../../components/ui/EmptyState';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { SkeletonCard } from '../../components/ui/Skeleton';
import { formatLocalDateTime, formatLocalTimeRange, formatCurrency } from '../../lib/formatters';
import {
  CalendarDays,
  Clock,
  RotateCw,
  AlertCircle,
  X,
  ArrowRight,
} from 'lucide-react';

export default function BookingsPage() {
  useDocumentTitle('My Bookings');

  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Cancellation dialog state
  const [cancelBookingTarget, setCancelBookingTarget] = useState(null);
  const [isCancelling, setIsCancelling] = useState(false);

  const { success, error: toastError } = useToast();

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setLoading(true);
    }
    setError(null);
    try {
      const response = await client.get('/api/v1/me/bookings');
      setBookings(response.data || []);
    } catch (err) {
      console.error('Error fetching bookings:', err);
      setError(err.response?.data?.detail || 'Failed to load bookings.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(false);
  }, [fetchData]);

  const handleConfirmCancel = async () => {
    if (!cancelBookingTarget) return;
    setIsCancelling(true);
    try {
      const response = await client.post(`/api/v1/bookings/${cancelBookingTarget.id}/cancel`);
      const msg = response.data?.candidate_selected
        ? 'Booking cancelled. Waitlist candidate has been automatically selected with a temporary hold.'
        : 'Booking cancelled successfully.';
      success(msg);
      setCancelBookingTarget(null);
      await fetchData(true);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to cancel booking.';
      toastError(msg);
    } finally {
      setIsCancelling(false);
    }
  };

  const now = Date.now();

  const upcomingBookings = useMemo(() => {
    return bookings.filter((b) => {
      if (b.status !== 'CONFIRMED') return false;
      const startTime = new Date(b.slot?.start_time).getTime();
      return isNaN(startTime) || startTime >= now;
    });
  }, [bookings, now]);

  const pastBookings = useMemo(() => {
    return bookings.filter((b) => {
      if (b.status !== 'CONFIRMED') return false;
      const startTime = new Date(b.slot?.start_time).getTime();
      return !isNaN(startTime) && startTime < now;
    });
  }, [bookings, now]);

  const cancelledBookings = useMemo(() => {
    return bookings.filter((b) => b.status === 'CANCELLED');
  }, [bookings]);

  const renderBookingGrid = (list, emptyMessage) => {
    if (list.length === 0) {
      return (
        <EmptyState
          icon={CalendarDays}
          title="No bookings in this section"
          description={emptyMessage}
          action={
            <Link to="/slots">
              <Button variant="primary" size="sm">
                Browse open slots
              </Button>
            </Link>
          }
        />
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {list.map((booking) => {
          const isConfirmed = booking.status === 'CONFIRMED';
          const isRecovered = Boolean(
            booking.recovered_from_booking_id || booking.source === 'RECOVERED'
          );

          return (
            <Card
              key={booking.id}
              hover
              className="flex flex-col justify-between"
            >
              <div>
                {/* Header: Resource & Status */}
                <div className="flex items-start justify-between gap-2 pb-3 mb-3 border-b border-zinc-100">
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-900 tracking-tight">
                      {booking.slot?.resource_id || 'Reserved Appointment'}
                    </h3>
                    <span className="text-[11px] font-mono text-zinc-400">
                      Booking #{booking.id}
                    </span>
                  </div>
                  <Badge status={booking.status} size="sm" />
                </div>

                <div className="space-y-2.5 text-xs">
                  {booking.status === 'CANCELLED' && booking.cancellation_reason && (
                    <p className="text-zinc-500">Reason: {booking.cancellation_reason}</p>
                  )}
                  {/* Recovered from waitlist chip on RECOVERED bookings */}
                  {isRecovered && (
                    <div className="mb-2">
                      <Badge status="RECOVERED" size="sm">
                        Recovered from waitlist
                      </Badge>
                    </div>
                  )}

                  {/* Schedule */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-zinc-800 font-medium">
                      <Clock className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                      <span>{formatLocalDateTime(booking.slot?.start_time)}</span>
                    </div>
                    <div className="text-[11px] text-zinc-500 pl-5.5">
                      {formatLocalTimeRange(booking.slot?.start_time, booking.slot?.end_time)}
                    </div>
                  </div>

                  {/* Price */}
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-zinc-500">Total price</span>
                    <span className="font-semibold text-zinc-900">
                      {formatCurrency(booking.slot?.price)}
                    </span>
                  </div>

                  <div className="text-[11px] text-zinc-400 pt-1">
                    Booked {formatLocalDateTime(booking.booked_at)}
                  </div>
                </div>
              </div>

              {/* Card Footer: Cancel Button */}
              {isConfirmed && (
                <div className="mt-4 pt-3 border-t border-zinc-100 flex justify-end">
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={X}
                    onClick={() => setCancelBookingTarget(booking)}
                  >
                    Cancel booking
                  </Button>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900">
            My Bookings
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Manage your confirmed appointments and view cancellation records.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/slots">
            <Button variant="secondary" size="sm">
              <span>Find more slots</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </Link>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchData(true)}
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
          <Button variant="secondary" size="sm" onClick={() => fetchData(true)}>
            Retry
          </Button>
        </div>
      )}

      {/* Main Content with Tabs: Upcoming / Past / Cancelled */}
      {loading ? (
        <SkeletonCard count={3} />
      ) : (
        <Tabs defaultValue="upcoming" className="space-y-5">
          <TabsList>
            <TabsTrigger value="upcoming">
              Upcoming ({upcomingBookings.length})
            </TabsTrigger>
            <TabsTrigger value="past">
              Past ({pastBookings.length})
            </TabsTrigger>
            <TabsTrigger value="cancelled">
              Cancelled ({cancelledBookings.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upcoming">
            {renderBookingGrid(
              upcomingBookings,
              'You have no upcoming appointments. Browse our open slots to reserve a time.'
            )}
          </TabsContent>

          <TabsContent value="past">
            {renderBookingGrid(
              pastBookings,
              'No past appointments logged on your account.'
            )}
          </TabsContent>

          <TabsContent value="cancelled">
            {renderBookingGrid(
              cancelledBookings,
              'No cancelled bookings on your account.'
            )}
          </TabsContent>
        </Tabs>
      )}

      {/* CONFIRMATION DIALOG: CANCEL BOOKING */}
      <ConfirmDialog
        isOpen={Boolean(cancelBookingTarget)}
        title="Cancel Appointment Booking?"
        description={
          cancelBookingTarget ? (
            <span>
              Are you sure you want to cancel your confirmed booking for{' '}
              <strong className="text-zinc-900 font-semibold">
                {cancelBookingTarget.slot?.resource_id || 'this slot'}
              </strong>
              ? It will be immediately offered to candidates waiting in the priority queue.
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
        onClose={() => !isCancelling && setCancelBookingTarget(null)}
      />
    </div>
  );
}
