import * as DialogPrimitive from '@radix-ui/react-dialog';
import Button from './Button';
import { AlertCircle, X } from 'lucide-react';

export default function ConfirmDialog({
  isOpen,
  title = 'Are you sure?',
  description = 'This action cannot be undone.',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmVariant = 'danger',
  isLoading = false,
  onConfirm,
  onClose,
}) {
  return (
    <DialogPrimitive.Root open={Boolean(isOpen)} onOpenChange={(open) => !open && !isLoading && onClose?.()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/30 backdrop-blur-xs transition-opacity animate-in fade-in-0 duration-150" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl border border-zinc-200 duration-150 animate-in fade-in-0 zoom-in-95 focus:outline-none">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-700 shrink-0">
                <AlertCircle className="w-5 h-5 text-zinc-700" />
              </div>
              <DialogPrimitive.Title className="text-base font-semibold text-zinc-900">
                {title}
              </DialogPrimitive.Title>
            </div>
            <button
              type="button"
              onClick={() => !isLoading && onClose?.()}
              className="text-zinc-400 hover:text-zinc-600 p-1 rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
              aria-label="Close dialog"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <DialogPrimitive.Description className="mt-3 text-xs text-zinc-600 leading-relaxed">
            {description}
          </DialogPrimitive.Description>

          <div className="mt-6 flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-100">
            <Button
              variant="secondary"
              size="sm"
              disabled={isLoading}
              onClick={() => !isLoading && onClose?.()}
            >
              {cancelText}
            </Button>
            <Button
              variant={confirmVariant}
              size="sm"
              isLoading={isLoading}
              onClick={onConfirm}
            >
              {confirmText}
            </Button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
