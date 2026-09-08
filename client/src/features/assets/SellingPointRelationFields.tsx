import { Button } from '@client/src/components/ui/button';
import { Select } from '@client/src/components/ui/select';
import type { BusinessConcept } from '@client/src/types/api';

interface SellingPointRelationFieldsProps {
  concepts: BusinessConcept[];
  primaryConceptId: string;
  supportConceptIds: string[];
  disabled?: boolean;
  onPrimaryConceptChange: (value: string) => void;
  onSupportConceptIdsChange: (value: string[]) => void;
}

export function SellingPointRelationFields({
  concepts,
  primaryConceptId,
  supportConceptIds,
  disabled = false,
  onPrimaryConceptChange,
  onSupportConceptIdsChange,
}: SellingPointRelationFieldsProps) {
  const supportIds = new Set(supportConceptIds);

  return (
    <div className="space-y-4">
      <label className="block">
        <span className="field-label">主要表达</span>
        <Select
          value={primaryConceptId}
          disabled={disabled}
          onChange={(event) => {
            const next = event.target.value;
            onPrimaryConceptChange(next);
            if (next) {
              onSupportConceptIdsChange(supportConceptIds.filter((id) => id !== next));
            }
          }}
        >
          <option value="">暂不选择</option>
          {concepts.map((concept) => (
            <option key={concept.id} value={concept.id}>{concept.name}</option>
          ))}
        </Select>
        <span className="field-hint">选择这张图最直接表达的一个卖点。</span>
      </label>

      <div>
        <span className="field-label">同时可以支持</span>
        <div className="mt-1.5 flex flex-wrap gap-2">
          {concepts
            .filter((concept) => concept.id !== primaryConceptId)
            .map((concept) => {
              const selected = supportIds.has(concept.id);
              return (
                <Button
                  key={concept.id}
                  type="button"
                  size="sm"
                  variant={selected ? 'default' : 'outline'}
                  disabled={disabled}
                  className={selected ? 'bg-foreground text-background hover:bg-foreground/88' : undefined}
                  aria-pressed={selected}
                  onClick={() => onSupportConceptIdsChange(
                    selected
                      ? supportConceptIds.filter((id) => id !== concept.id)
                      : [...supportConceptIds, concept.id],
                  )}
                >
                  {concept.name}
                </Button>
              );
            })}
        </div>
        <span className="field-hint">可多选。选择它还能证明或辅助表达的其他卖点。</span>
      </div>
    </div>
  );
}
