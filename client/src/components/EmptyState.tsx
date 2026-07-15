import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="surface-card flex min-h-64 flex-col items-center justify-center px-6 py-14 text-center">
      <div className="flex size-12 items-center justify-center rounded-2xl bg-accent text-primary">
        {icon}
      </div>
      <h2 className="mt-4 text-base font-semibold text-foreground">{title}</h2>
      {description && <p className="mt-1.5 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
