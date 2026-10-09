import { useState, useEffect, useCallback, Fragment } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import client from '../../api/client';
import { useToast } from '../../context/useToast';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Countdown from '../../components/ui/Countdown';
import EmptyState from '../../components/ui/EmptyState';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import { SkeletonTable } from '../../components/ui/Skeleton';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table';
import { formatLocalDateTime, formatLocalTimeRange, formatCurrency } from '../../lib/formatters';
import {
  Plus,
  RotateCw,
  AlertCircle,
  MoreHorizontal,
  X,
  Users,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export default function BusinessSlotsPage() {
  useDocumentTitle('Business Slots');

  const [slots, setSlots] = useState([]);
  const [waitlistMap, setWaitlistMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Expanded rows set for waitlist preview
  const [expandedSlotIds, setExpandedSlotIds] = useState(new Set());

  // Create Slot Dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    resource_id: '',
    start_time: '',
    end_time: '',
    price: '',
  });
  const [formErrors, setFormErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Cancel booking target state
  const [cancelTargetSlot, setCancelTargetSlot] = useState(null);
  const [isCancelling, setIsCancelling] = useState(false);

  const { success, error: toastError } = useToast();

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setLoading(true);
    }
    setError(null);
    try {
      const [slotsRes, waitlistRes] = await Promise.all([
        client.get('/api/v1/business/slots'),
        client.get('/api/v1/business/waitlist'),
      ]);
      setSlots(slotsRes.data || []);

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
    fetchData(false);
  }, [fetchData]);

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
      const startIso = formData.start_time ? new Date(formData.start_time).toISOString() : '';
      const endIso = formData.end_time ? new Date(formData.end_time).toISOString() : '';
      const priceNum = formData.price === '' ? 0 : parseFloat(formData.price);

      await client.post('/api/v1/slots', {
        resource_id: formData.resource_id,
        start_time: startIso,
        end_time: endIso,
        price: isNaN(priceNum) ? 0 : priceNum,
      });

      success(`Slot for "${formData.resource_id}" published successfully.`);
      setFormData({
        resource_id: '',
        start_time: '',
        end_time: '',
        price: '',
      });
      setCreateDialogOpen(false);
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
        ? 'Booking cancelled. Waitlist candidate has been automatically offered a temporary hold.'
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900">
            Resource Slots
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Publish openings, inspect holders, and monitor automated cancellation holds.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchData(true)}
            icon={RotateCw}
            disabled={loading}
            aria-label="Refresh slots"
          >
            Refresh
          </Button>

          <Button
            variant="primary"
            size="sm"
            icon={Plus}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create slot
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

      {/* Main Linear-Style Table */}
      {loading ? (
        <SkeletonTable rows={6} cols={6} />
      ) : slots.length === 0 ? (
        <EmptyState
          icon={Plus}
          title="No slots created yet"
          description="Publish your first resource opening using the Create Slot dialog to start accepting bookings and waitlists."
          action={
            <Button variant="primary" size="sm" onClick={() => setCreateDialogOpen(true)}>
              Create first slot
            </Button>
          }
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow hover={false}>
              <TableHead>Resource</TableHead>
              <TableHead>Time Range</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Current Holder</TableHead>
              <TableHead>Offer Holder / Countdown</TableHead>
              <TableHead align="center">Waitlist</TableHead>
              <TableHead align="right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {slots.map((slot) => {
              const isBooked = slot.status === 'BOOKED';
              const isHeld = slot.status === 'HELD';
              const isExpanded = expandedSlotIds.has(slot.id);
              const slotWaitlist = waitlistMap[slot.id] || [];

              return (
                <Fragment key={slot.id}>
                  <TableRow>
                    {/* Resource */}
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-semibold text-zinc-900">{slot.resource_id}</span>
                        <span className="text-[11px] text-zinc-400 font-mono">
                          {slot.id}
                        </span>
                      </div>
                    </TableCell>

                    {/* Schedule */}
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="text-zinc-900 font-medium">
                          {formatLocalDateTime(slot.start_time)}
                        </span>
                        <span className="text-[11px] text-zinc-500">
                          {formatLocalTimeRange(slot.start_time, slot.end_time)}
                        </span>
                      </div>
                    </TableCell>

                    {/* Status Pill */}
                    <TableCell>
                      <Badge status={slot.status} size="sm" />
                    </TableCell>

                    {/* Price */}
                    <TableCell>
                      <span className="font-semibold text-zinc-900">
                        {formatCurrency(slot.price)}
                      </span>
                    </TableCell>

                    {/* Current Holder */}
                    <TableCell>
                      {isBooked ? (
                        <span className="font-medium text-zinc-900">
                          {slot.active_booking_holder_name || 'Booked Client'}
                        </span>
                      ) : (
                        <span className="text-zinc-400">—</span>
                      )}
                    </TableCell>

                    {/* Offer Holder with Countdown */}
                    <TableCell>
                      {isHeld ? (
                        <div className="flex flex-col gap-1 max-w-[160px]">
                          <span className="font-medium text-amber-700 text-xs">
                            {slot.active_hold_holder_name || 'Candidate'}
                          </span>
                          <Countdown
                            expiresAt={slot.active_hold_expires_at}
                            totalDurationSeconds={300}
                            size="sm"
                          />
                        </div>
                      ) : (
                        <span className="text-zinc-400">—</span>
                      )}
                    </TableCell>

                    {/* Waitlist count & toggle */}
                    <TableCell align="center">
                      <button
                        type="button"
                        onClick={() => toggleExpandSlot(slot.id)}
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                          slot.waitlist_count > 0
                            ? 'bg-zinc-100 text-zinc-800 hover:bg-zinc-200'
                            : 'text-zinc-400 hover:text-zinc-600'
                        }`}
                        title="Toggle waitlist entries"
                      >
                        <Users className="w-3.5 h-3.5" />
                        <span>{slot.waitlist_count}</span>
                        {isExpanded ? (
                          <ChevronUp className="w-3 h-3 ml-0.5" />
                        ) : (
                          <ChevronDown className="w-3 h-3 ml-0.5" />
                        )}
                      </button>
                    </TableCell>

                    {/* Row Actions Menu: Radix Dropdown */}
                    <TableCell align="right">
                      <DropdownMenu.Root>
                        <DropdownMenu.Trigger asChild>
                          <button
                            type="button"
                            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 cursor-pointer"
                            aria-label={`Actions for slot ${slot.resource_id}`}
                          >
                            <MoreHorizontal className="w-4 h-4" />
                          </button>
                        </DropdownMenu.Trigger>

                        <DropdownMenu.Portal>
                          <DropdownMenu.Content
                            align="end"
                            sideOffset={4}
                            className="z-50 min-w-[180px] rounded-lg bg-white p-1 shadow-lg border border-zinc-200 text-xs duration-150 animate-in fade-in-0 zoom-in-95 focus:outline-none"
                          >
                            <DropdownMenu.Item
                              onSelect={() => toggleExpandSlot(slot.id)}
                              className="px-2.5 py-1.5 rounded-md hover:bg-zinc-100 text-zinc-700 cursor-pointer focus:outline-none focus:bg-zinc-100"
                            >
                              {isExpanded ? 'Hide waitlist' : 'View waitlist'}
                            </DropdownMenu.Item>

                            {isBooked && (
                              <>
                                <DropdownMenu.Separator className="h-px bg-zinc-100 my-1" />
                                <DropdownMenu.Item
                                  onSelect={() => setCancelTargetSlot(slot)}
                                  className="px-2.5 py-1.5 rounded-md hover:bg-rose-50 text-rose-600 cursor-pointer focus:outline-none focus:bg-rose-50"
                                >
                                  Cancel booking
                                </DropdownMenu.Item>
                              </>
                            )}
                          </DropdownMenu.Content>
                        </DropdownMenu.Portal>
                      </DropdownMenu.Root>
                    </TableCell>
                  </TableRow>

                  {/* Expanded Waitlist View */}
                  {isExpanded && (
                    <TableRow hover={false} className="bg-zinc-50/70 border-b border-zinc-200">
                      <td colSpan={8} className="px-6 py-4">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                              Waitlist queue for {slot.resource_id} ({slotWaitlist.length} candidates)
                            </span>
                          </div>

                          {slotWaitlist.length === 0 ? (
                            <p className="text-xs text-zinc-400 italic">
                              No candidates currently in the waitlist queue for this slot.
                            </p>
                          ) : (
                            <div className="border border-zinc-200 rounded-lg overflow-hidden bg-white">
                              <table className="w-full text-xs text-left">
                                <thead className="bg-zinc-50 border-b border-zinc-100 text-[11px] font-medium text-zinc-500 uppercase">
                                  <tr>
                                    <th className="px-3 py-2">Position</th>
                                    <th className="px-3 py-2">Customer</th>
                                    <th className="px-3 py-2">Status</th>
                                    <th className="px-3 py-2">Joined</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-zinc-100">
                                  {slotWaitlist.map((entry) => (
                                    <tr key={entry.id} className="hover:bg-zinc-50/60">
                                      <td className="px-3 py-2 font-bold text-zinc-900">
                                        #{entry.position || 1}
                                      </td>
                                      <td className="px-3 py-2 font-medium text-zinc-900">
                                        {entry.user_name || entry.user_id}
                                      </td>
                                      <td className="px-3 py-2">
                                        <Badge status={entry.status} size="sm" />
                                      </td>
                                      <td className="px-3 py-2 text-zinc-500">
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
                    </TableRow>
                  )}
                </Fragment>
              );
            })}
          </TableBody>
        </Table>
      )}

      {/* CREATE SLOT DIALOG (using @radix-ui/react-dialog) */}
      <DialogPrimitive.Root open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/30 backdrop-blur-xs animate-in fade-in-0 duration-150" />
          <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl border border-zinc-200 duration-150 animate-in fade-in-0 zoom-in-95 focus:outline-none">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
              <div>
                <DialogPrimitive.Title className="text-base font-semibold text-zinc-900">
                  Create Time Slot
                </DialogPrimitive.Title>
                <DialogPrimitive.Description className="text-xs text-zinc-500 mt-0.5">
                  Publish a resource opening with start/end time and price.
                </DialogPrimitive.Description>
              </div>
              <DialogPrimitive.Close asChild>
                <button
                  type="button"
                  className="text-zinc-400 hover:text-zinc-600 p-1 rounded-md"
                  aria-label="Close dialog"
                >
                  <X className="w-4 h-4" />
                </button>
              </DialogPrimitive.Close>
            </div>

            {formErrors.general && (
              <div className="mt-3 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{formErrors.general}</span>
              </div>
            )}

            <form onSubmit={handleCreateSlot} className="mt-4 space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-zinc-700 mb-1">
                  Resource Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.resource_id}
                  onChange={(e) => handleInputChange('resource_id', e.target.value)}
                  placeholder="e.g. Consultation Room 2"
                  className="w-full bg-white border border-zinc-200 rounded-lg px-3 py-2 text-xs text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
                {formErrors.resource_id && (
                  <p className="mt-1 text-xs text-rose-600">{formErrors.resource_id}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-zinc-700 mb-1">
                    Start Time *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={formData.start_time}
                    onChange={(e) => handleInputChange('start_time', e.target.value)}
                    className="w-full bg-white border border-zinc-200 rounded-lg px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                  {formErrors.start_time && (
                    <p className="mt-1 text-xs text-rose-600">{formErrors.start_time}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-700 mb-1">
                    End Time *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={formData.end_time}
                    onChange={(e) => handleInputChange('end_time', e.target.value)}
                    className="w-full bg-white border border-zinc-200 rounded-lg px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                  {formErrors.end_time && (
                    <p className="mt-1 text-xs text-rose-600">{formErrors.end_time}</p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 mb-1">
                  Price (INR ₹)
                </label>
                <input
                  type="number"
                  step="1"
                  min="0"
                  value={formData.price}
                  onChange={(e) => handleInputChange('price', e.target.value)}
                  placeholder="1500"
                  className="w-full bg-white border border-zinc-200 rounded-lg px-3 py-2 text-xs text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
                {formErrors.price && (
                  <p className="mt-1 text-xs text-rose-600">{formErrors.price}</p>
                )}
              </div>

              <div className="mt-6 pt-3 border-t border-zinc-100 flex items-center justify-end gap-2.5">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={isSubmitting}
                  onClick={() => setCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  isLoading={isSubmitting}
                >
                  Publish Slot
                </Button>
              </div>
            </form>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>

      {/* CONFIRM DIALOG: CANCEL BOOKING */}
      <ConfirmDialog
        isOpen={Boolean(cancelTargetSlot)}
        title="Cancel Client Booking?"
        description={
          cancelTargetSlot ? (
            <span>
              Are you sure you want to cancel the booking for{' '}
              <strong className="text-zinc-900 font-semibold">
                {cancelTargetSlot.active_booking_holder_name || 'this client'}
              </strong>{' '}
              on resource <strong className="text-zinc-900 font-semibold">{cancelTargetSlot.resource_id}</strong>?
              The system will automatically dispatch an offer to the next waitlisted customer.
            </span>
          ) : (
            'Are you sure you want to cancel this booking?'
          )
        }
        confirmText="Cancel Booking"
        cancelText="Keep Booking"
        confirmVariant="danger"
        isLoading={isCancelling}
        onConfirm={handleConfirmCancelBooking}
        onClose={() => !isCancelling && setCancelTargetSlot(null)}
      />
    </div>
  );
}
