import { Select } from '@client/src/components/ui/select';
import type {
  BusinessConcept,
  BusinessFacetCatalog,
} from '@client/src/types/api';

const sourceLevelNames: Record<string, string> = {
  system: '体系',
  selling_point: '核心卖点',
  proof_group: '来源分支',
  evidence_expression: '绿色点',
};

interface BusinessClassificationFieldsProps {
  concepts: BusinessConcept[];
  facets: BusinessFacetCatalog;
  conceptId: string;
  proofPointCode: string;
  evidencePointCode: string;
  disabled?: boolean;
  onConceptChange: (value: string) => void;
  onProofPointChange: (value: string) => void;
  onEvidencePointChange: (value: string) => void;
}

export function BusinessClassificationFields({
  concepts,
  facets,
  conceptId,
  proofPointCode,
  evidencePointCode,
  disabled = false,
  onConceptChange,
  onProofPointChange,
  onEvidencePointChange,
}: BusinessClassificationFieldsProps) {
  const concept = concepts.find((item) => item.id === conceptId);
  const proofs = facets.proofPoints.filter((point) => point.conceptCode === concept?.code);
  const evidence = facets.evidencePoints.filter(
    (point) => point.proofPointCode === proofPointCode,
  );
  const selectedEvidence = evidence.find((point) => point.code === evidencePointCode);

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="block">
        <span className="field-label">主要表达卖点</span>
        <Select
          value={conceptId}
          disabled={disabled}
          onChange={(event) => onConceptChange(event.target.value)}
        >
          <option value="">暂不标注</option>
          {concepts.map((item) => (
            <option key={item.id} value={item.id}>{item.name}</option>
          ))}
        </Select>
      </label>
      <label className="block">
        <span className="field-label">证明点</span>
        <Select
          value={proofPointCode}
          disabled={disabled || !conceptId}
          onChange={(event) => onProofPointChange(event.target.value)}
        >
          <option value="">暂不标注</option>
          {proofs.map((point) => (
            <option key={point.code} value={point.code}>{point.name}</option>
          ))}
        </Select>
      </label>
      <label className="block">
        <span className="field-label">证据表达点</span>
        <Select
          value={evidencePointCode}
          disabled={disabled || !proofPointCode}
          onChange={(event) => onEvidencePointChange(event.target.value)}
        >
          <option value="">暂不标注</option>
          {evidence.map((point) => (
            <option key={point.code} value={point.code}>{point.name}</option>
          ))}
        </Select>
      </label>
      {selectedEvidence && (selectedEvidence.sourcePaths?.length ?? 0) > 0 && (
        <details className="rounded-xl border border-primary/10 bg-primary/[0.025] px-4 py-3 sm:col-span-3">
          <summary className="cursor-pointer text-sm font-medium text-foreground">
            查看原图推导路径
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              {selectedEvidence.sourceRef}
            </span>
          </summary>
          <div className="mt-3 space-y-3">
            {selectedEvidence.sourcePaths?.map((sourcePath, pathIndex) => (
              <div
                key={`${selectedEvidence.code}-${pathIndex}`}
                className="rounded-lg border border-border/70 bg-card px-3 py-2.5"
              >
                {(selectedEvidence.sourcePaths?.length ?? 0) > 1 && (
                  <div className="mb-2 text-xs font-medium text-muted-foreground">
                    来源路径 {pathIndex + 1}
                  </div>
                )}
                <ol className="space-y-1.5">
                  {sourcePath.map((node, nodeIndex) => (
                    <li
                      key={`${node.level}-${nodeIndex}`}
                      className="grid grid-cols-[4.5rem_1fr] gap-2 text-xs leading-5"
                    >
                      <span className="text-muted-foreground">
                        {sourceLevelNames[node.level] ?? node.level}
                      </span>
                      <span className="text-foreground">
                        {node.label}
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            ))}
            {(selectedEvidence.reviewNotes?.length ?? 0) > 0 && (
              <div className="rounded-lg border border-amber-200/80 bg-amber-50/70 px-3 py-2.5">
                <div className="mb-1 text-xs font-medium text-amber-900">
                  人工确认关系
                </div>
                <ul className="space-y-1 text-xs leading-5 text-amber-950/80">
                  {selectedEvidence.reviewNotes?.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </details>
      )}
    </div>
  );
}
