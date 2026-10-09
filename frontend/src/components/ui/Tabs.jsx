import * as TabsPrimitive from '@radix-ui/react-tabs';
import { cn } from '../../lib/utils';

export const Tabs = TabsPrimitive.Root;

export function TabsList({ className = '', children, ...props }) {
  return (
    <TabsPrimitive.List
      className={cn(
        'inline-flex items-center gap-1 p-1 bg-zinc-100 rounded-lg border border-zinc-200/60',
        className
      )}
      {...props}
    >
      {children}
    </TabsPrimitive.List>
  );
}

export function TabsTrigger({ className = '', children, ...props }) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-medium text-zinc-600 transition-all cursor-pointer',
        'hover:text-zinc-900',
        'data-[state=active]:bg-white data-[state=active]:text-zinc-900 data-[state=active]:shadow-xs data-[state=active]:font-semibold',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-1',
        className
      )}
      {...props}
    >
      {children}
    </TabsPrimitive.Trigger>
  );
}

export const TabsContent = TabsPrimitive.Content;

export default Tabs;
