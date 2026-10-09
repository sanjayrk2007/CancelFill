import { cn } from '../../lib/utils';

export default function Badge({
  status,
  variant,
  children,
  className = '',
  size = 'md',
}) {
  const normalizedStatus = (status || (typeof children === 'string' ? children : ''))
    .toString()
    .toUpperCase();

  const getStyles = () => {
    // 2. Status colors only on badges: AVAILABLE green, BOOKED slate, HELD amber, CONFIRMED green, CANCELLED red, EXPIRED/DECLINED slate, RECOVERED blue.
    if (variant === 'green' || normalizedStatus === 'AVAILABLE' || normalizedStatus === 'CONFIRMED') {
      return {
        badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        dot: 'bg-emerald-500',
      };
    }
    if (variant === 'amber' || normalizedStatus === 'HELD' || normalizedStatus === 'OFFER ACTIVE') {
      return {
        badge: 'bg-amber-50 text-amber-700 border-amber-200',
        dot: 'bg-amber-500',
      };
    }
    if (variant === 'red' || normalizedStatus === 'CANCELLED') {
      return {
        badge: 'bg-rose-50 text-rose-700 border-rose-200',
        dot: 'bg-rose-500',
      };
    }
    if (variant === 'blue' || normalizedStatus === 'RECOVERED') {
      return {
        badge: 'bg-blue-50 text-blue-700 border-blue-200',
        dot: 'bg-blue-500',
      };
    }
    if (
      variant === 'slate' ||
      normalizedStatus === 'BOOKED' ||
      normalizedStatus === 'EXPIRED' ||
      normalizedStatus === 'DECLINED' ||
      normalizedStatus === 'WAITING' ||
      normalizedStatus === 'OFFERED'
    ) {
      return {
        badge: 'bg-zinc-100 text-zinc-700 border-zinc-200',
        dot: 'bg-zinc-400',
      };
    }

    // Default neutral
    return {
      badge: 'bg-zinc-100 text-zinc-700 border-zinc-200',
      dot: 'bg-zinc-400',
    };
  };

  const { badge, dot } = getStyles();

  const sizeStyles =
    size === 'sm'
      ? 'px-2 py-0.5 text-[11px]'
      : size === 'lg'
      ? 'px-3 py-1 text-sm'
      : 'px-2.5 py-0.5 text-xs';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium tracking-tight whitespace-nowrap',
        badge,
        sizeStyles,
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', dot)} />
      <span>{children || status}</span>
    </span>
  );
}
