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

  const getVariantStyles = () => {
    if (variant === 'green' || normalizedStatus === 'AVAILABLE') {
      return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    }
    if (variant === 'gray' || normalizedStatus === 'BOOKED') {
      return 'bg-slate-500/15 text-slate-300 border-slate-500/30';
    }
    if (variant === 'amber' || normalizedStatus === 'HELD') {
      return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
    }
    if (normalizedStatus === 'CONFIRMED') {
      return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    }
    if (normalizedStatus === 'WAITING') {
      return 'bg-sky-500/15 text-sky-300 border-sky-500/30';
    }
    if (normalizedStatus === 'OFFERED') {
      return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
    }
    if (
      normalizedStatus === 'CANCELLED' ||
      normalizedStatus === 'EXPIRED' ||
      normalizedStatus === 'DECLINED'
    ) {
      return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
    }
    if (normalizedStatus === 'CUSTOMER') {
      return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
    }
    if (normalizedStatus === 'BUSINESS') {
      return 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30';
    }
    return 'bg-slate-800 text-slate-300 border-slate-700';
  };

  const getDotStyles = () => {
    if (variant === 'green' || normalizedStatus === 'AVAILABLE') return 'bg-emerald-400';
    if (variant === 'gray' || normalizedStatus === 'BOOKED') return 'bg-slate-400';
    if (variant === 'amber' || normalizedStatus === 'HELD') return 'bg-amber-400';
    if (normalizedStatus === 'CONFIRMED') return 'bg-emerald-400';
    if (normalizedStatus === 'WAITING') return 'bg-sky-400';
    if (normalizedStatus === 'OFFERED') return 'bg-purple-400 animate-pulse';
    if (
      normalizedStatus === 'CANCELLED' ||
      normalizedStatus === 'EXPIRED' ||
      normalizedStatus === 'DECLINED'
    )
      return 'bg-rose-400';
    if (normalizedStatus === 'CUSTOMER') return 'bg-cyan-400';
    if (normalizedStatus === 'BUSINESS') return 'bg-indigo-400';
    return 'bg-slate-400';
  };

  const sizeStyles =
    size === 'sm'
      ? 'px-2 py-0.5 text-xs'
      : size === 'lg'
      ? 'px-3.5 py-1.5 text-sm font-semibold'
      : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border tracking-wide uppercase font-semibold ${getVariantStyles()} ${sizeStyles} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${getDotStyles()}`} />
      {children || status}
    </span>
  );
}
