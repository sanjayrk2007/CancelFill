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
  CheckCircle,
  Clock,
  DollarSign,
  RotateCw,
  AlertCircle,
  CalendarDays,
  XCircle,
  Sparkles,
  ListOrdered,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';

export default function BookingsPage() {
  const [bookings, setBookings] = useState([]);
  const [waitlistEntries, setWaitlistEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Cancellation dialog state
  const [cancelBookingTarget, setCancelBookingTarget] = useState(null);
  const [isCancelling, setIsCancelling] = useState(false);

  // Leave waitlist dialog state
  const [leaveWaitlistTarget, setLeaveWaitlistTarget] = useState(null);
  const [isLeavingWaitlist, setIsLeavingWaitlist] = useState(false);

  const { success, error: toastError } = useToast();

  const fetchData = useCallback(async (isRefresh = false) => {
    if (!isRefresh) setLoading(true);
    setError(null);
    try {
      const [bookingsRes, waitlistRes] = await Promise.all([
        client.get('/api/v1/me/bookings'),
        client.get('/api/v1/me/waitlist'),
      ]);
      setBookings(bookingsRes.data || []);
      setWaitlistEntries(waitlistRes.data || []);
    } catch (err) {
      console.error('Error fetching bookings/waitlist:', err);
      setError(err.response?.data?.detail || 'Failed to load bookings and waitlist entries.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle Cancel Booking confirm
  const handleConfirmCancel = async () => {
    if (!cancelBookingTarget) return;
    setIsCancelling(true);
    try {
      const response = await client.post(`/api/v1/bookings/${cancelBookingTarget.id}/cancel`);
      const msg = response.data?.candidate_selected
        ? 'Booking cancelled. Waitlist candidate has been automatically selected with a temporary hold!'
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

  // Handle Leave Waitlist confirm
  const handleConfirmLeaveWaitlist = async () => {
    if (!leaveWaitlistTarget) return;
    setIsLeavingWaitlist(true);
    try {
      await client.delete(`/api/v1/waitlist/${leaveWaitlistTarget.id}`);
      success('Successfully left the waitlist.');
      setLeaveWaitlistTarget(null);
      await fetchData(true);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to leave waitlist.';
      toastError(msg);
    } finally {
      setIsLeavingWaitlist(false);
    }
  };

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/60">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              My Bookings & Waitlist
            </h1>
            <Badge status="CUSTOMER">CUSTOMER</Badge>
          </div>
          <p className="text-sm text-slate-400">
            Manage your confirmed appointments, cancellations, and real-time waitlist queue positions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchData(true)}
            icon={RotateCw}
            disabled={loading}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <span className="text-sm font-medium">{error}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={() => fetchData(false)}>
            Retry
          </Button>
        </div>
      )}

      {loading ? (
        <div className="min-h-[350px] flex flex-col items-center justify-center gap-3 p-12 border border-slate-800/80 rounded-2xl bg-slate-900/30">
          <Spinner size="lg" />
          <p className="text-sm text-slate-400">Loading your bookings and waitlist positions...</p>
        </div>
      ) : (
        <>
          {/* SECTION 1: MY BOOKINGS */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
                  Confirmed Bookings
                </h2>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                  {bookings.length}
                </span>
              </div>
              <Link
                to="/slots"
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
              >
                <span>Browse more slots</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {bookings.length === 0 ? (
              <Card>
                <CardContent className="pt-6">
                  <EmptyState
                    icon={CalendarDays}
                    title="No Bookings Yet"
                    description="You don't have any booked appointments. Browse our open slots to make a reservation."
                    action={
                      <Link to="/slots">
                        <Button variant="primary" size="sm">
                          Browse Open Slots
                        </Button>
                      </Link>
                    }
                  />
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {bookings.map((booking) => {
                  const isConfirmed = booking.status === 'CONFIRMED';
                  const isRecovered = Boolean(booking.recovered_from_booking_id);

                  return (
                    <Card
                      key={booking.id}
                      hover
                      className={`flex flex-col justify-between border-slate-800 bg-slate-900/90 ${
                        isConfirmed ? 'border-emerald-500/20' : 'opacity-80'
                      }`}
                    >
                      <div>
                        <CardHeader className="pb-3 border-b border-slate-800/60">
                          <div className="flex items-start justify-between gap-2">
                            <div className="truncate">
                              <CardTitle className="text-base truncate">
                                {booking.slot?.resource_id || 'Reserved Slot'}
                              </CardTitle>
                              <CardDescription className="text-xs text-slate-400 mt-0.5 truncate">
                                Booking: {booking.id}
                              </CardDescription>
                            </div>
                            <Badge status={booking.status} size="sm" />
                          </div>
                        </CardHeader>

                        <CardContent className="space-y-3 pt-1">
                          {/* Recovery indicator */}
                          {isRecovered && (
                            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-semibold">
                              <Sparkles className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                              <span>Recovered from waitlist</span>
                            </div>
                          )}

                          {/* Date and time */}
                          <div className="flex items-start gap-2.5 text-slate-300">
                            <Clock className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
                            <div className="text-xs">
                              <div className="font-semibold text-slate-200">
                                {formatLocalDateTime(booking.slot?.start_time)}
                              </div>
                              <div className="text-slate-400 text-[11px] mt-0.5">
                                {formatLocalTimeRange(booking.slot?.start_time, booking.slot?.end_time)}
                              </div>
                            </div>
                          </div>

                          {/* Price */}
                          <div className="flex items-center gap-2.5 text-slate-300">
                            <DollarSign className="w-4 h-4 text-emerald-400 shrink-0" />
                            <div className="text-xs font-semibold text-emerald-300">
                              {formatCurrency(booking.slot?.price)}
                            </div>
                          </div>
                        </CardContent>
                      </div>

                      {/* Footer: Cancel button with dialog trigger */}
                      <CardFooter className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between">
                        <span className="text-[11px] text-slate-400">
                          Booked: {formatLocalDateTime(booking.booked_at)}
                        </span>

                        {isConfirmed && (
                          <Button
                            variant="danger"
                            size="sm"
                            icon={XCircle}
                            onClick={() => setCancelBookingTarget(booking)}
                          >
                            Cancel
                          </Button>
                        )}
                      </CardFooter>
                    </Card>
                  );
                })}
              </div>
            )}
          </section>

          {/* SECTION 2: MY WAITLIST */}
          <section className="space-y-4 pt-6 border-t border-slate-800/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Clock className="w-5 h-5 text-sky-400" />
                <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
                  My Waitlist Entries
                </h2>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                  {waitlistEntries.length}
                </span>
              </div>
              <Link
                to="/offers"
                className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1 font-medium"
              >
                <span>Check offers inbox</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {waitlistEntries.length === 0 ? (
              <Card>
                <CardContent className="pt-6">
                  <EmptyState
                    icon={Clock}
                    title="No Waitlist Entries"
                    description="You are not waiting for any booked slots. If a slot you want is taken, join its waitlist to be automatically notified when cancellations occur."
                    action={
                      <Link to="/slots">
                        <Button variant="secondary" size="sm">
                          Browse Slots to Join
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
                          {/* Queue Position Badge */}
                          <div className="flex items-center gap-2 p-2 rounded-xl bg-sky-950/40 border border-sky-500/30 text-sky-200">
                            <ListOrdered className="w-4 h-4 text-sky-400 shrink-0" />
                            <div className="text-xs font-semibold">
                              {entry.priority_order
                                ? `Queue Position #${entry.priority_order}`
                                : 'Queue Position #1'}
                            </div>
                          </div>

                          {/* Slot Date and time */}
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

                      {/* Footer: Leave waitlist button */}
                      <CardFooter className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between">
                        <span className="text-[11px] text-slate-400">
                          Joined: {formatLocalDateTime(entry.joined_at)}
                        </span>

                        {isWaiting && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-rose-400 hover:text-rose-300 hover:border-rose-500/50"
                            onClick={() => setLeaveWaitlistTarget(entry)}
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
          </section>
        </>
      )}

      {/* CONFIRMATION DIALOG: CANCEL BOOKING */}
      <ConfirmDialog
        isOpen={Boolean(cancelBookingTarget)}
        title="Cancel Appointment Booking?"
        description={
          cancelBookingTarget ? (
            <div className="space-y-2">
              <p>
                Are you sure you want to cancel your confirmed booking for{' '}
                <strong className="text-white">
                  {cancelBookingTarget.slot?.resource_id || 'this slot'}
                </strong>
                ?
              </p>
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
                <span>
                  The slot will immediately be offered to waitlisted candidates via automated recovery.
                </span>
              </div>
            </div>
          ) : (
            'Are you sure you want to cancel this booking?'
          )
        }
        confirmText="Yes, Cancel Booking"
        cancelText="Keep Booking"
        confirmVariant="danger"
        isLoading={isCancelling}
        onConfirm={handleConfirmCancel}
        onClose={() => !isCancelling && setCancelBookingTarget(null)}
      />

      {/* CONFIRMATION DIALOG: LEAVE WAITLIST */}
      <ConfirmDialog
        isOpen={Boolean(leaveWaitlistTarget)}
        title="Leave Waitlist Queue?"
        description={
          leaveWaitlistTarget ? (
            <p>
              Are you sure you want to leave the waitlist for{' '}
              <strong className="text-white">
                {leaveWaitlistTarget.slot?.resource_id || 'this slot'}
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
        isLoading={isLeavingWaitlist}
        onConfirm={handleConfirmLeaveWaitlist}
        onClose={() => !isLeavingWaitlist && setLeaveWaitlistTarget(null)}
      />
    </div>
  );
}
