import { cn } from '../../lib/utils';

export default function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  className = '',
}) {
  return (
    <div
      className={cn(
        'bg-white border border-zinc-200 rounded-xl p-5 shadow-xs flex flex-col justify-between',
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
          {label}
        </span>
        {Icon && (
          <div className="w-7 h-7 rounded-lg bg-zinc-50 border border-zinc-100 flex items-center justify-center text-zinc-500 shrink-0">
            <Icon className="w-3.5 h-3.5" />
          </div>
        )}
      </div>

      <div className="mt-3">
        <div className="text-2xl sm:text-3xl font-semibold text-zinc-900 tracking-tight">
          {value}
        </div>
        {hint && (
          <p className="text-xs text-zinc-500 mt-1">
            {hint}
          </p>
        )}
      </div>
    </div>
  );
}
