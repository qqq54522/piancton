import { Select } from '@client/src/components/ui/select';
import type {
  BusinessConcept,
  BusinessFacetCatalog,
} from '@client/src/types/api';

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
  const evidencePoints = facets.evidencePoints.filter((point) => (
    point.conceptCode === concept?.code
    && (!proofPointCode || point.proofPointCode === proofPointCode)
  ));

  return (
    <div className="grid gap-4 lg:grid-cols-3">
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
          disabled={disabled || !conceptId || !proofPointCode}
          onChange={(event) => onEvidencePointChange(event.target.value)}
        >
          <option value="">暂不标注</option>
          {evidencePoints.map((point) => (
            <option key={point.code} value={point.code}>{point.name}</option>
          ))}
        </Select>
      </label>
    </div>
  );
}
