import { useRef } from 'react';
import { Link } from 'react-router-dom';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import Button from './Button';
import { CheckCircle2, Clock, CalendarDays, Tag, X } from 'lucide-react';
import { formatLocalDateTime, formatLocalTimeRange, formatCurrency } from '../../lib/formatters';

export default function BookingConfirmationDialog({
  isOpen,
  booking,
  onClose,
}) {
  const closeRef = useRef(null);

  if (!booking) return null;

  const slot = booking.slot || {};
  const startTime = slot.start_time || booking.start_time;
  const endTime = slot.end_time || booking.end_time;
  const resourceName = slot.resource_id || booking.resource_id || 'Appointment';
  const businessName = slot.business_name || booking.business_name;
  const price = slot.price ?? booking.price;
  const bookingId = booking.id || booking.booking_id;

  return (
    <DialogPrimitive.Root open={Boolean(isOpen)} onOpenChange={(open) => !open && onClose?.()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs transition-opacity animate-in fade-in-0 duration-150" />
        <DialogPrimitive.Content
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            closeRef.current?.focus();
          }}
          className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white p-6 shadow-2xl border border-zinc-200 duration-150 animate-in fade-in-0 zoom-in-95 focus:outline-none"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 border border-emerald-100">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <DialogPrimitive.Title className="text-base font-semibold text-zinc-900">
                  Booking Confirmed!
                </DialogPrimitive.Title>
                <DialogPrimitive.Description className="text-xs text-zinc-500">
                  Your appointment slot has been reserved.
                </DialogPrimitive.Description>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="text-zinc-400 hover:text-zinc-600 p-1 rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 cursor-pointer"
              aria-label="Close dialog"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="mt-5 space-y-3 rounded-xl border border-zinc-200 bg-zinc-50/70 p-4 text-xs">
            {bookingId && (
              <div className="flex items-center justify-between pb-2.5 border-b border-zinc-200/80">
                <span className="text-zinc-500 font-medium">Booking ID</span>
                <span className="font-mono font-semibold text-zinc-900">#{bookingId}</span>
              </div>
            )}

            <div>
              {businessName && (
                <div className="text-[11px] font-semibold text-blue-600 uppercase tracking-wider mb-0.5">
                  {businessName}
                </div>
              )}
              <div className="text-sm font-semibold text-zinc-900">{resourceName}</div>
            </div>

            <div className="flex items-center gap-2 text-zinc-700">
              <CalendarDays className="w-4 h-4 text-zinc-400 shrink-0" />
              <span>{formatLocalDateTime(startTime)}</span>
            </div>

            {endTime && (
              <div className="flex items-center gap-2 text-zinc-500 pl-6 text-[11px]">
                <Clock className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                <span>{formatLocalTimeRange(startTime, endTime)}</span>
              </div>
            )}

            {price !== undefined && price !== null && (
              <div className="flex items-center justify-between pt-2.5 border-t border-zinc-200/80">
                <span className="text-zinc-500 flex items-center gap-1.5">
                  <Tag className="w-3.5 h-3.5 text-zinc-400" />
                  Amount
                </span>
                <span className="font-semibold text-zinc-900">{formatCurrency(price)}</span>
              </div>
            )}
          </div>

          <div className="mt-6 flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-100">
            <Button
              ref={closeRef}
              variant="secondary"
              size="sm"
              onClick={onClose}
            >
              Done
            </Button>
            <Link to="/bookings" onClick={onClose}>
              <Button variant="primary" size="sm">
                View My Bookings
              </Button>
            </Link>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
