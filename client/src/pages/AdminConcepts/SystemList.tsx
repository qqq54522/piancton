import { ChevronRight, Network } from 'lucide-react';

import type { TagWithCount } from '@client/src/types/api';

interface SystemListProps {
  systems: TagWithCount[];
  selectedId?: string;
  sellingPointCount: (systemId: string) => number;
  onSelect: (systemId: string) => void;
}

export default function SystemList({
  systems,
  selectedId,
  sellingPointCount,
  onSelect,
}: SystemListProps) {
  return (
    <aside className="surface-card flex min-h-0 flex-col overflow-hidden lg:h-full lg:self-start">
      <div className="shrink-0 border-b border-border px-4 py-3.5">
        <p className="text-sm font-semibold">业务体系</p>
        <p className="mt-1 text-xs text-muted-foreground">选择体系，查看它包含的卖点</p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2 compact-scrollbar">
        {systems.map((system) => {
          const active = system.id === selectedId;
          return (
            <button
              key={system.id}
              type="button"
              onClick={() => onSelect(system.id)}
              className={`mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition-colors ${
                active ? 'bg-accent text-accent-foreground' : 'hover:bg-secondary'
              }`}
            >
              <span className={`flex size-9 shrink-0 items-center justify-center rounded-xl ${
                active ? 'bg-primary text-primary-foreground' : 'bg-secondary text-muted-foreground'
              }`}>
                <Network className="size-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold">{system.name}</span>
                <span className="mt-0.5 block text-[11px] text-muted-foreground">
                  {sellingPointCount(system.id)} 个卖点
                </span>
              </span>
              <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
            </button>
          );
        })}
      </div>
    </aside>
  );
}
