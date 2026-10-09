import { cn } from '../../lib/utils';

function getInitials(name) {
  if (!name || typeof name !== 'string') return '?';
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function Avatar({
  name = '',
  initials,
  size = 'md',
  className = '',
}) {
  const displayInitials = initials || getInitials(name);

  const sizeClasses = {
    xs: 'w-6 h-6 text-[10px]',
    sm: 'w-7 h-7 text-xs',
    md: 'w-8 h-8 text-xs',
    lg: 'w-10 h-10 text-sm',
    xl: 'w-12 h-12 text-base',
  };

  return (
    <div
      className={cn(
        'rounded-full bg-zinc-100 border border-zinc-200 text-zinc-700 font-semibold flex items-center justify-center select-none shrink-0',
        sizeClasses[size] || sizeClasses.md,
        className
      )}
      title={name || displayInitials}
    >
      <span>{displayInitials}</span>
    </div>
  );
}
