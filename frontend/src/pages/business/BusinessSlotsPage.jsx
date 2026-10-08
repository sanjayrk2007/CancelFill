import { useState, useEffect, useCallback, Fragment } from 'react';
import client from '../../api/client';
import { useToast } from '../../context/useToast';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Spinner from '../../components/ui/Spinner';
import EmptyState from '../../components/ui/EmptyState';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import { formatLocalDateTime, formatLocalTimeRange, formatCurrency, formatRemainingSeconds } from '../../lib/formatters';
import {
  Layers,
  PlusCircle,
  Users,
  ChevronDown,
  ChevronUp,
  XCircle,
  RotateCw,
  AlertCircle,
  User,
  Timer,
} from 'lucide-react';

export default function BusinessSlotsPage() {
  const [slots, setSlots] = useState([]);
  const [waitlistMap, setWaitlistMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Expanded rows set
  const [expandedSlotIds, setExpandedSlotIds] = useState(new Set());

  // Form state
  const [formData, setFormData] = useState({
    resource_id: '',
    start_time: '',
    end_time: '',
    price: '',
  });
  const [formErrors, setFormErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Cancel dialog state
  const [cancelTargetSlot, setCancelTargetSlot] = useState(null);
  const [isCancelling, setIsCancelling] = useState(false);

  // Live timer tick for HELD countdowns
  const [currentTime, setCurrentTime] = useState(() => Date.now());

  const { success, error: toastError } = useToast();

  useEffect(() => {
    const timerId = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);
    return () => clearInterval(timerId);
  }, []);

  const fetchData = useCallback(async (isRefresh = false) => {
    if (!isRefresh) setLoading(true);
    setError(null);
    try {
      const [slotsRes, waitlistRes] = await Promise.all([
        client.get('/api/v1/business/slots'),
        client.get('/api/v1/business/waitlist'),
      ]);
      setSlots(slotsRes.data || []);

      // Index waitlist by slot_id
      const map = {};
      (waitlistRes.data || []).forEach((w) => {
        map[w.slot_id] = w.entries || [];
      });
      setWaitlistMap(map);
    } catch (err) {
      console.error('Error fetching business slots:', err);
      setError(err.response?.data?.detail || 'Failed to load business slots.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Parse API 422 validation errors
  const parseValidationErrors = (err) => {
    const fieldErrors = {};
    let generalMessage = 'Validation failed. Please correct the fields below.';

    if (!err?.response) {
      return { fieldErrors: {}, generalMessage: err?.message || 'Network error occurred.' };
    }

    const detail = err.response.data?.detail;
    if (typeof detail === 'string') {
      generalMessage = detail;
      if (detail.includes('end_time') || detail.includes('start_time')) {
        fieldErrors.end_time = detail;
      }
    } else if (Array.isArray(detail)) {
      detail.forEach((item) => {
        const field = item.loc && item.loc[item.loc.length - 1];
        if (field && field !== 'body') {
          fieldErrors[field] = item.msg;
        } else {
          generalMessage = item.msg || generalMessage;
        }
      });
    }
    return { fieldErrors, generalMessage };
  };

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for that field
    if (formErrors[field] || formErrors.general) {
      setFormErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        delete next.general;
        return next;
      });
    }
  };

  const handleCreateSlot = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setFormErrors({});

    try {
      // Format timestamps to ISO UTC
      const startIso = formData.start_time ? new Date(formData.start_time).toISOString() : '';
      const endIso = formData.end_time ? new Date(formData.end_time).toISOString() : '';
      const priceNum = formData.price === '' ? 0 : parseFloat(formData.price);

      await client.post('/api/v1/slots', {
        resource_id: formData.resource_id,
        start_time: startIso,
        end_time: endIso,
        price: isNaN(priceNum) ? 0 : priceNum,
      });

      success(`Slot for "${formData.resource_id}" created successfully!`);
      setFormData({
        resource_id: '',
        start_time: '',
        end_time: '',
        price: '',
      });
      await fetchData(true);
    } catch (err) {
      const { fieldErrors, generalMessage } = parseValidationErrors(err);
      setFormErrors({ ...fieldErrors, general: generalMessage });
      toastError(generalMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleExpandSlot = (slotId) => {
    setExpandedSlotIds((prev) => {
      const next = new Set(prev);
      if (next.has(slotId)) {
        next.delete(slotId);
      } else {
        next.add(slotId);
      }
      return next;
    });
  };

  const handleConfirmCancelBooking = async () => {
    if (!cancelTargetSlot?.active_booking_id) return;
    setIsCancelling(true);
    try {
      const res = await client.post(`/api/v1/bookings/${cancelTargetSlot.active_booking_id}/cancel`);
      const msg = res.data?.candidate_selected
        ? 'Booking cancelled. Waitlist candidate has been automatically offered a temporary hold!'
        : 'Booking cancelled successfully.';
      success(msg);
      setCancelTargetSlot(null);
      await fetchData(true);
    } catch (err) {
      toastError(err.response?.data?.detail || 'Failed to cancel booking.');
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/60">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Resource Slot Management
            </h1>
            <Badge status="BUSINESS">BUSINESS</Badge>
          </div>
          <p className="text-sm text-slate-400">
            Publish time slots, monitor live status and holders, cancel bookings to trigger recovery, and inspect waitlists.
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

      {/* Global Error */}
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

      {/* 1. CREATE SLOT FORM */}
      <Card className="border-indigo-500/20 bg-slate-900/90 shadow-xl">
        <CardHeader className="pb-3 border-b border-slate-800/60">
          <div className="flex items-center gap-2">
            <PlusCircle className="w-5 h-5 text-indigo-400" />
            <CardTitle className="text-lg text-white">Create New Time Slot</CardTitle>
          </div>
          <CardDescription>
            Publish a resource slot with local start/end times and price.
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-4">
          {formErrors.general && (
            <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{formErrors.general}</span>
            </div>
          )}

          <form onSubmit={handleCreateSlot} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Resource ID */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Resource Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.resource_id}
                  onChange={(e) => handleInputChange('resource_id', e.target.value)}
                  placeholder="e.g. Room 101, Dr. Smith"
                  className={`w-full bg-slate-950/70 border rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 transition-all ${
                    formErrors.resource_id
                      ? 'border-rose-500 focus:ring-rose-500/40'
                      : 'border-slate-700/80 focus:ring-indigo-500/40 focus:border-indigo-500'
                  }`}
                />
                {formErrors.resource_id && (
                  <p className="mt-1 text-xs text-rose-400">{formErrors.resource_id}</p>
                )}
              </div>

              {/* Start Time */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Start Time *
                </label>
                <input
                  type="datetime-local"
                  required
                  value={formData.start_time}
                  onChange={(e) => handleInputChange('start_time', e.target.value)}
                  className={`w-full bg-slate-950/70 border rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 transition-all ${
                    formErrors.start_time
                      ? 'border-rose-500 focus:ring-rose-500/40'
                      : 'border-slate-700/80 focus:ring-indigo-500/40 focus:border-indigo-500'
                  }`}
                />
                {formErrors.start_time && (
                  <p className="mt-1 text-xs text-rose-400">{formErrors.start_time}</p>
                )}
              </div>

              {/* End Time */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  End Time *
                </label>
                <input
                  type="datetime-local"
                  required
                  value={formData.end_time}
                  onChange={(e) => handleInputChange('end_time', e.target.value)}
                  className={`w-full bg-slate-950/70 border rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 transition-all ${
                    formErrors.end_time
                      ? 'border-rose-500 focus:ring-rose-500/40'
                      : 'border-slate-700/80 focus:ring-indigo-500/40 focus:border-indigo-500'
                  }`}
                />
                {formErrors.end_time && (
                  <p className="mt-1 text-xs text-rose-400">{formErrors.end_time}</p>
                )}
              </div>

              {/* Price */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Price ($ USD)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.price}
                  onChange={(e) => handleInputChange('price', e.target.value)}
                  placeholder="50.00"
                  className={`w-full bg-slate-950/70 border rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 transition-all ${
                    formErrors.price
                      ? 'border-rose-500 focus:ring-rose-500/40'
                      : 'border-slate-700/80 focus:ring-indigo-500/40 focus:border-indigo-500'
                  }`}
                />
                {formErrors.price && (
                  <p className="mt-1 text-xs text-rose-400">{formErrors.price}</p>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={isSubmitting}
                icon={PlusCircle}
              >
                Create Slot
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* 2. SLOTS TABLE */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h2 className="text-xl font-bold text-white tracking-tight">Active Slots & Recovery State</h2>
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {slots.length}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="min-h-[300px] flex flex-col items-center justify-center gap-3 p-12 border border-slate-800/80 rounded-2xl bg-slate-900/30">
            <Spinner size="lg" />
            <p className="text-sm text-slate-400">Loading your published slots...</p>
          </div>
        ) : slots.length === 0 ? (
          <Card>
            <CardContent className="pt-6">
              <EmptyState
                icon={Layers}
                title="No Slots Created Yet"
                description="You have not published any resource slots yet. Use the form above to add your first appointment opening."
              />
            </CardContent>
          </Card>
        ) : (
          <div className="border border-slate-800 rounded-2xl bg-slate-900/80 overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/80 text-xs font-semibold uppercase text-slate-400 tracking-wider border-b border-slate-800">
                  <tr>
                    <th scope="col" className="px-5 py-3.5">Resource</th>
                    <th scope="col" className="px-5 py-3.5">Time</th>
                    <th scope="col" className="px-5 py-3.5">Status</th>
                    <th scope="col" className="px-5 py-3.5">Price</th>
                    <th scope="col" className="px-5 py-3.5">Current Holder</th>
                    <th scope="col" className="px-5 py-3.5 text-center">Waitlist</th>
                    <th scope="col" className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {slots.map((slot) => {
                    const isBooked = slot.status === 'BOOKED';
                    const isHeld = slot.status === 'HELD';
                    const isExpanded = expandedSlotIds.has(slot.id);
                    const slotWaitlist = waitlistMap[slot.id] || [];

                    // Countdown for HELD slot
                    let heldCountdown = null;
                    if (isHeld && slot.active_hold_expires_at) {
                      const expiresMs = new Date(slot.active_hold_expires_at).getTime();
                      const secondsRemaining = Math.max(0, Math.floor((expiresMs - currentTime) / 1000));
                      heldCountdown = formatRemainingSeconds(secondsRemaining);
                    }

                    return (
                      <Fragment key={slot.id}>
                        <tr className="hover:bg-slate-850/50 transition-colors">
                          {/* Resource */}
                          <td className="px-5 py-4 font-medium text-white">
                            <div className="flex flex-col">
                              <span className="font-semibold text-slate-100">{slot.resource_id}</span>
                              <span className="text-[11px] text-slate-500 font-mono mt-0.5 truncate max-w-[140px]">
                                {slot.id}
                              </span>
                            </div>
                          </td>

                          {/* Time */}
                          <td className="px-5 py-4 text-xs">
                            <div className="flex flex-col gap-0.5">
                              <span className="text-slate-200 font-medium">
                                {formatLocalDateTime(slot.start_time)}
                              </span>
                              <span className="text-slate-400 text-[11px]">
                                {formatLocalTimeRange(slot.start_time, slot.end_time)}
                              </span>
                            </div>
                          </td>

                          {/* Status */}
                          <td className="px-5 py-4">
                            <Badge status={slot.status} size="sm" />
                          </td>

                          {/* Price */}
                          <td className="px-5 py-4 font-semibold text-emerald-400">
                            {formatCurrency(slot.price)}
                          </td>

                          {/* Current Holder & HELD Countdown */}
                          <td className="px-5 py-4 text-xs">
                            {isBooked ? (
                              <div className="flex items-center gap-1.5 text-slate-200">
                                <User className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                                <span className="font-medium">
                                  {slot.active_booking_holder_name || 'Booked Customer'}
                                </span>
                              </div>
                            ) : isHeld ? (
                              <div className="flex flex-col gap-1">
                                <div className="flex items-center gap-1.5 text-amber-300 font-medium">
                                  <User className="w-3.5 h-3.5 shrink-0" />
                                  <span>{slot.active_hold_holder_name || 'Candidate'}</span>
                                </div>
                                <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-mono animate-pulse">
                                  <Timer className="w-3 h-3 shrink-0" />
                                  <span>Expires in {heldCountdown || '00:00'}</span>
                                </div>
                              </div>
                            ) : (
                              <span className="text-slate-500 italic">—</span>
                            )}
                          </td>

                          {/* Waitlist count & toggle */}
                          <td className="px-5 py-4 text-center">
                            <button
                              type="button"
                              onClick={() => toggleExpandSlot(slot.id)}
                              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                                slot.waitlist_count > 0
                                  ? 'bg-sky-500/15 text-sky-300 border border-sky-500/30 hover:bg-sky-500/25'
                                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                              }`}
                              title="Toggle waitlist entries"
                            >
                              <Users className="w-3.5 h-3.5" />
                              <span>{slot.waitlist_count}</span>
                              {isExpanded ? (
                                <ChevronUp className="w-3.5 h-3.5 ml-0.5" />
                              ) : (
                                <ChevronDown className="w-3.5 h-3.5 ml-0.5" />
                              )}
                            </button>
                          </td>

                          {/* Actions */}
                          <td className="px-5 py-4 text-right">
                            {isBooked && (
                              <Button
                                variant="danger"
                                size="sm"
                                icon={XCircle}
                                onClick={() => setCancelTargetSlot(slot)}
                              >
                                Cancel booking
                              </Button>
                            )}
                          </td>
                        </tr>

                        {/* Expandable Waitlist Details */}
                        {isExpanded && (
                          <tr className="bg-slate-950/60 border-t border-b border-slate-800">
                            <td colSpan={7} className="px-6 py-4">
                              <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                                    <Users className="w-4 h-4 text-sky-400" />
                                    <span>Waitlist Queue for {slot.resource_id}</span>
                                    <span className="text-slate-500 font-normal">
                                      ({slotWaitlist.length} candidates)
                                    </span>
                                  </h4>
                                </div>

                                {slotWaitlist.length === 0 ? (
                                  <p className="text-xs text-slate-500 italic py-2">
                                    No candidates are currently on the waitlist for this slot.
                                  </p>
                                ) : (
                                  <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/60">
                                    <table className="w-full text-left text-xs text-slate-300">
                                      <thead className="bg-slate-950/80 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                                        <tr>
                                          <th className="px-4 py-2">Position</th>
                                          <th className="px-4 py-2">Customer Name</th>
                                          <th className="px-4 py-2">Status</th>
                                          <th className="px-4 py-2">Joined At</th>
                                        </tr>
                                      </thead>
                                      <tbody className="divide-y divide-slate-800/50">
                                        {slotWaitlist.map((entry) => (
                                          <tr key={entry.id} className="hover:bg-slate-850/40">
                                            <td className="px-4 py-2.5 font-bold text-sky-300">
                                              #{entry.position || 1}
                                            </td>
                                            <td className="px-4 py-2.5 text-white font-medium">
                                              {entry.user_name || entry.user_id}
                                            </td>
                                            <td className="px-4 py-2.5">
                                              <Badge status={entry.status} size="sm" />
                                            </td>
                                            <td className="px-4 py-2.5 text-slate-400">
                                              {formatLocalDateTime(entry.joined_at)}
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* CANCEL BOOKING CONFIRM DIALOG */}
      <ConfirmDialog
        isOpen={Boolean(cancelTargetSlot)}
        title="Cancel Confirmed Booking?"
        description={
          cancelTargetSlot ? (
            <div className="space-y-2">
              <p>
                Are you sure you want to cancel the confirmed booking for{' '}
                <strong className="text-white">
                  {cancelTargetSlot.active_booking_holder_name || 'this customer'}
                </strong>{' '}
                on resource <strong className="text-white">{cancelTargetSlot.resource_id}</strong>?
              </p>
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>
                  The slot will immediately be offered to waitlisted candidates with a temporary hold.
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
        onConfirm={handleConfirmCancelBooking}
        onClose={() => !isCancelling && setCancelTargetSlot(null)}
      />
    </div>
  );
}
