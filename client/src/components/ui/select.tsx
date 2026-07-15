import * as React from 'react';
import { ChevronDown } from 'lucide-react';

import { cn } from '@client/src/lib/utils';

function Select({ className, ...props }: React.ComponentProps<'select'>) {
  return (
    <div className="relative w-full">
      <select
        data-slot="select"
        className={cn(
          'h-10 w-full appearance-none rounded-xl border border-input bg-card py-2 pl-3.5 pr-11 text-sm text-foreground shadow-xs outline-none transition-[border-color,box-shadow] enabled:hover:border-ring/50 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/15 disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60',
          className,
        )}
        {...props}
      />
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute right-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
      />
    </div>
  );
}

export { Select };
