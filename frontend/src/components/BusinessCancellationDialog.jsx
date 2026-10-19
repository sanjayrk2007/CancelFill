import { useNavigate } from 'react-router-dom';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import Button from './ui/Button';
import { useNotifications } from '../context/useNotifications';
import { formatLocalDateTime } from '../lib/formatters';
import { CalendarX2, X } from 'lucide-react';

export default function BusinessCancellationDialog() {
  const { cancellationAlerts, dismissCancellationAlert } = useNotifications();
  const navigate = useNavigate();

  const current = cancellationAlerts[0] || null;
  const remaining = Math.max(0, cancellationAlerts.length - 1);

  const handleClose = () => {
    if (current) dismissCancellationAlert(current.id);
  };

  const handleViewBookings = () => {
    if (current) dismissCancellationAlert(current.id);
    navigate('/bookings');
  };

  return (
    <DialogPrimitive.Root open={Boolean(current)} onOpenChange={(open) => !open && handleClose()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs animate-in fade-in-0 duration-150" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl border border-rose-200 duration-150 animate-in fade-in-0 zoom-in-95 focus:outline-none">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-rose-50 flex items-center justify-center shrink-0">
                <CalendarX2 className="w-5 h-5 text-rose-600" />
              </div>
              <DialogPrimitive.Title className="text-base font-semibold text-zinc-900">
                {current?.title || 'Your appointment was cancelled by the business'}
              </DialogPrimitive.Title>
            </div>
            <button
              type="button"
              onClick={handleClose}
              className="text-zinc-400 hover:text-zinc-600 p-1 rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 cursor-pointer"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <DialogPrimitive.Description className="mt-4 text-xs text-zinc-700 leading-relaxed">
            {current?.body}
          </DialogPrimitive.Description>

          {current?.created_at && (
            <p className="mt-2 text-[11px] text-zinc-400">
              Cancelled {formatLocalDateTime(current.created_at)}
            </p>
          )}

          <p className="mt-3 text-[11px] text-zinc-500 leading-relaxed">
            Any payment for this booking is refunded automatically. You can rejoin the waitlist or
            book another slot from the Slots page.
          </p>

          {remaining > 0 && (
            <p className="mt-3 text-[11px] font-medium text-rose-700">
              {remaining} more cancelled {remaining === 1 ? 'appointment' : 'appointments'} to review
            </p>
          )}

          <div className="mt-6 flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-100">
            <Button variant="secondary" size="sm" onClick={handleClose}>
              {remaining > 0 ? 'Next' : 'Dismiss'}
            </Button>
            <Button variant="primary" size="sm" onClick={handleViewBookings}>
              View my bookings
            </Button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
