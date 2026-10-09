import { Inbox } from 'lucide-react';
import { cn } from '../../lib/utils';

export default function EmptyState({
  icon: Icon = Inbox,
  title = 'No items found',
  description = 'There are no records to display at this moment.',
  action,
  children,
  className = '',
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center p-8 sm:p-12 border border-dashed border-zinc-200 rounded-xl bg-white/60',
        className
      )}
    >
      <div className="w-10 h-10 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-500 mb-3">
        <Icon className="w-5 h-5 text-zinc-600" />
      </div>
      <h4 className="text-sm font-semibold text-zinc-900 mb-1">{title}</h4>
      <p className="text-xs text-zinc-500 max-w-sm mb-4 leading-relaxed">
        {description}
      </p>
      {action && <div>{action}</div>}
      {children}
    </div>
  );
}
