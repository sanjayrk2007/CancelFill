import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  icon: Icon,
  type = 'button',
  className = '',
  onClick,
  ...props
}) {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-lg transition-colors cursor-pointer select-none disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2';

  const variants = {
    primary:
      'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white shadow-xs focus-visible:ring-blue-600 focus-visible:ring-offset-white border border-transparent',
    secondary:
      'bg-white hover:bg-zinc-50 active:bg-zinc-100 text-zinc-900 border border-zinc-200 shadow-xs focus-visible:ring-zinc-400 focus-visible:ring-offset-white',
    ghost:
      'bg-transparent hover:bg-zinc-100 active:bg-zinc-200 text-zinc-700 hover:text-zinc-900 focus-visible:ring-zinc-400 focus-visible:ring-offset-white border border-transparent',
    danger:
      'bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white shadow-xs focus-visible:ring-rose-600 focus-visible:ring-offset-white border border-transparent',
    outline:
      'bg-white hover:bg-zinc-50 active:bg-zinc-100 text-zinc-900 border border-zinc-200 shadow-xs focus-visible:ring-zinc-400 focus-visible:ring-offset-white',
    // Fallback for previous variants
    emerald:
      'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white shadow-xs focus-visible:ring-blue-600 focus-visible:ring-offset-white border border-transparent',
  };

  const sizes = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5 h-8',
    md: 'text-sm px-3.5 py-2 gap-2 h-9',
    lg: 'text-sm px-4 py-2.5 gap-2 h-10 font-semibold',
  };

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={cn(baseStyles, variants[variant] || variants.primary, sizes[size] || sizes.md, className)}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin shrink-0" />
          <span>{children}</span>
        </>
      ) : (
        <>
          {Icon && <Icon className="w-4 h-4 shrink-0" />}
          {children}
        </>
      )}
    </button>
  );
}
