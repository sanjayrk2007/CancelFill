import { useState, useEffect } from 'react';
import { formatRemainingSeconds } from '../../lib/formatters';
import { cn } from '../../lib/utils';

export default function Countdown({
  expiresAt,
  totalDurationSeconds = 300,
  className = '',
  size = 'md',
}) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  if (!expiresAt) {
    return <span className="font-mono text-xs text-zinc-400">--:--</span>;
  }

  const expiresMs = new Date(expiresAt).getTime();
  const secondsRemaining = Math.max(0, Math.floor((expiresMs - now) / 1000));
  const percentLeft = Math.min(100, Math.max(0, (secondsRemaining / totalDurationSeconds) * 100));

  const isUnder10s = secondsRemaining <= 10 && secondsRemaining > 0;
  const isUnder30Percent = percentLeft <= 30 && secondsRemaining > 0;
  const isExpired = secondsRemaining === 0;

  // Determine color scheme
  let barColor = 'bg-blue-600';
  let textColor = 'text-zinc-900';

  if (isExpired) {
    barColor = 'bg-zinc-300';
    textColor = 'text-zinc-400';
  } else if (isUnder10s) {
    barColor = 'bg-rose-600';
    textColor = 'text-rose-600';
  } else if (isUnder30Percent) {
    barColor = 'bg-amber-500';
    textColor = 'text-amber-600';
  }

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <div className="flex items-center justify-between gap-2">
        <span
          className={cn(
            'font-mono font-semibold tracking-tight transition-colors',
            size === 'lg' ? 'text-2xl sm:text-3xl' : 'text-sm',
            textColor
          )}
        >
          {isExpired ? '00:00' : formatRemainingSeconds(secondsRemaining)}
        </span>
        {size === 'lg' && (
          <span className="text-xs text-zinc-500">
            {isExpired ? 'Expired' : 'Hold active'}
          </span>
        )}
      </div>

      {/* Depleting progress bar */}
      <div className="w-full bg-zinc-100 rounded-full h-1.5 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-1000 ease-linear', barColor)}
          style={{ width: `${percentLeft}%` }}
        />
      </div>
    </div>
  );
}
