import { ChevronRight, Tags } from 'lucide-react';

import type { BusinessConcept } from '@client/src/types/api';

interface ConceptListProps {
  concepts: BusinessConcept[];
  selectedId?: string;
  onSelect: (conceptId: string) => void;
}

export default function ConceptList({ concepts, selectedId, onSelect }: ConceptListProps) {
  return (
    <aside className="surface-card flex min-h-0 flex-col overflow-hidden lg:h-full lg:self-start">
      <div className="shrink-0 border-b border-border px-4 py-3.5">
        <p className="text-sm font-semibold">卖点目录</p>
        <p className="mt-1 text-xs text-muted-foreground">当前用于图片归属和火山路由映射</p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2 compact-scrollbar">
        {concepts.map((concept) => {
          const active = concept.id === selectedId;
          return (
            <button
              key={concept.id}
              type="button"
              onClick={() => onSelect(concept.id)}
              className={`mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition-colors ${
                active ? 'bg-accent text-accent-foreground' : 'hover:bg-secondary'
              }`}
            >
              <span className={`flex size-9 shrink-0 items-center justify-center rounded-xl ${
                active ? 'bg-primary text-primary-foreground' : 'bg-secondary text-muted-foreground'
              }`}>
                <Tags className="size-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold">{concept.name}</span>
                <span className="mt-0.5 block text-[11px] text-muted-foreground">
                  {concept.code}
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
