import { cn } from '../../lib/utils';

export function Table({ children, className = '', ...props }) {
  return (
    <div className={cn('w-full overflow-x-auto border border-zinc-200 rounded-xl bg-white shadow-xs', className)}>
      <table className="w-full text-left border-collapse text-sm text-zinc-900" {...props}>
        {children}
      </table>
    </div>
  );
}

export function TableHeader({ children, className = '', ...props }) {
  return (
    <thead
      className={cn(
        'sticky top-0 z-10 bg-zinc-50 border-b border-zinc-200 text-xs font-medium text-zinc-500 uppercase tracking-wider select-none',
        className
      )}
      {...props}
    >
      {children}
    </thead>
  );
}

export function TableBody({ children, className = '', ...props }) {
  return (
    <tbody className={cn('divide-y divide-zinc-100 bg-white', className)} {...props}>
      {children}
    </tbody>
  );
}

export function TableRow({ children, className = '', hover = true, ...props }) {
  return (
    <tr
      className={cn(
        hover && 'hover:bg-zinc-50/80 transition-colors',
        className
      )}
      {...props}
    >
      {children}
    </tr>
  );
}

export function TableHead({ children, className = '', align = 'left', ...props }) {
  return (
    <th
      scope="col"
      className={cn(
        'px-4 py-3 text-xs font-medium text-zinc-500 whitespace-nowrap',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
        align === 'left' && 'text-left',
        className
      )}
      {...props}
    >
      {children}
    </th>
  );
}

export function TableCell({ children, className = '', align = 'left', ...props }) {
  return (
    <td
      className={cn(
        'px-4 py-3 text-sm text-zinc-700 whitespace-nowrap',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
        align === 'left' && 'text-left',
        className
      )}
      {...props}
    >
      {children}
    </td>
  );
}

export default Table;
