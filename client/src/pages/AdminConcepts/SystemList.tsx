import { ChevronDown, ChevronRight, Network } from 'lucide-react';

import type { BusinessConcept, TagWithCount } from '@client/src/types/api';

interface SystemListProps {
  systems: TagWithCount[];
  conceptsBySystem: Map<string, BusinessConcept[]>;
  selectedSystemId?: string;
  selectedConceptId?: string;
  expandedSystemIds: Set<string>;
  onToggleSystem: (systemId: string) => void;
  onSelectConcept: (systemId: string, conceptId: string) => void;
}

export default function SystemList({
  systems,
  conceptsBySystem,
  selectedSystemId,
  selectedConceptId,
  expandedSystemIds,
  onToggleSystem,
  onSelectConcept,
}: SystemListProps) {
  return (
    <aside className="surface-card flex min-h-0 flex-col overflow-hidden lg:h-full lg:self-start">
      <div className="border-b border-border px-4 py-3.5">
        <p className="text-sm font-semibold">六大业务体系</p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2 compact-scrollbar">
        {systems.map((system) => {
          const expanded = expandedSystemIds.has(system.id);
          const sellingPoints = conceptsBySystem.get(system.id) ?? [];
          const systemActive = system.id === selectedSystemId;
          return (
            <div key={system.id} className="mb-1">
              <button
                type="button"
                onClick={() => onToggleSystem(system.id)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors ${
                  systemActive ? 'bg-secondary/80 text-foreground' : 'text-muted-foreground hover:bg-secondary/60 hover:text-foreground'
                }`}
              >
                <span className={`flex size-8 shrink-0 items-center justify-center rounded-lg ${
                  systemActive ? 'bg-foreground text-background' : 'bg-secondary text-muted-foreground'
                }`}>
                  <Network className="size-4" />
                </span>
                <span className="min-w-0 flex-1 truncate text-sm font-semibold">{system.name}</span>
                <span className="text-[11px] text-muted-foreground">{sellingPoints.length}</span>
                {expanded ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
              </button>

              {expanded && (
                <div className="ml-7 mt-1 border-l border-border/80 pl-3">
                  {sellingPoints.map((concept) => {
                    const active = concept.id === selectedConceptId;
                    return (
                      <button
                        key={concept.id}
                        type="button"
                        onClick={() => onSelectConcept(system.id, concept.id)}
                        className={`mb-1 flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                          active
                            ? 'bg-foreground font-semibold text-background'
                            : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                        }`}
                      >
                        <span className="truncate">{concept.name}</span>
                        <ChevronRight className={`size-3.5 shrink-0 ${active ? 'text-background/70' : ''}`} />
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
