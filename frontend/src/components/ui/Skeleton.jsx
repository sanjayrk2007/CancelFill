import { cn } from '../../lib/utils';

export default function Skeleton({ className = '', ...props }) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-zinc-200/80', className)}
      {...props}
    />
  );
}

export function SkeletonCard({ count = 3 }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-white border border-zinc-200 rounded-xl p-5 space-y-3">
          <div className="flex justify-between items-start">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          <Skeleton className="h-4 w-44" />
          <Skeleton className="h-4 w-24" />
          <div className="pt-2 border-t border-zinc-100 flex justify-end">
            <Skeleton className="h-8 w-24 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 5 }) {
  return (
    <div className="border border-zinc-200 rounded-xl bg-white overflow-hidden">
      <div className="border-b border-zinc-200 bg-zinc-50 px-4 py-3 flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      <div className="divide-y divide-zinc-100 p-4 space-y-3">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4 items-center">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton key={c} className="h-4 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
