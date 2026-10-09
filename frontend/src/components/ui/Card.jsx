import { cn } from '../../lib/utils';

export function Card({ children, className = '', hover = false, ...props }) {
  return (
    <div
      className={cn(
        'bg-white border border-zinc-200 rounded-xl shadow-xs p-5 transition-all',
        hover && 'hover:border-zinc-300 hover:shadow-sm',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '' }) {
  return (
    <div className={cn('flex flex-col gap-1 pb-3 mb-3 border-b border-zinc-100', className)}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '' }) {
  return (
    <h3 className={cn('text-base font-semibold text-zinc-900 tracking-tight', className)}>
      {children}
    </h3>
  );
}

export function CardDescription({ children, className = '' }) {
  return (
    <p className={cn('text-xs text-zinc-500 leading-relaxed', className)}>
      {children}
    </p>
  );
}

export function CardContent({ children, className = '' }) {
  return <div className={cn('space-y-3', className)}>{children}</div>;
}

export function CardFooter({ children, className = '' }) {
  return (
    <div className={cn('mt-4 pt-3 border-t border-zinc-100 flex items-center justify-between gap-3', className)}>
      {children}
    </div>
  );
}

export default Card;
