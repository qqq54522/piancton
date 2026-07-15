import * as React from 'react';

import { cn } from '@client/src/lib/utils';

function Select({ className, ...props }: React.ComponentProps<'select'>) {
  return (
    <select
      data-slot="select"
      className={cn(
        'h-10 w-full rounded-xl border border-input bg-card px-3.5 text-sm text-foreground shadow-xs outline-none transition-[border-color,box-shadow] enabled:hover:border-ring/50 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/15 disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60',
        className,
      )}
      {...props}
    />
  );
}

export { Select };
