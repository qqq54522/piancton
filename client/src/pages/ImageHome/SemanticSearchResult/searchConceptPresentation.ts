import type {
  ScoredImageMatch,
  SearchUnderstanding,
} from '@client/src/types/api';

export interface SearchIntentOption {
  name: string;
  weight: number;
}

export function searchProofPointOptions(
  understanding?: SearchUnderstanding,
): SearchIntentOption[] {
  return (understanding?.matchedProofPoints ?? [])
    .map((match) => ({ name: match.name, weight: match.weight }))
    .sort((left, right) => right.weight - left.weight)
    .slice(0, 4);
}

export function searchEvidencePointOptions(
  understanding?: SearchUnderstanding,
): SearchIntentOption[] {
  return (understanding?.matchedEvidencePoints ?? [])
    .map((match) => ({ name: match.name, weight: match.weight }))
    .sort((left, right) => right.weight - left.weight)
    .slice(0, 4);
}

export function searchIntentOptions(
  understanding?: SearchUnderstanding,
): SearchIntentOption[] {
  if (understanding?.queryType === 'ambiguous_business_intent_search') return [];
  const unique = new Map<string, SearchIntentOption>();
  for (const match of understanding?.matchedBusinessConcepts ?? []) {
    const name = displayConceptName(match.concept);
    const key = name.toLocaleLowerCase();
    const existing = unique.get(key);
    if (!existing || match.weight > existing.weight) {
      unique.set(key, { name, weight: match.weight });
    }
  }
  return [...unique.values()]
    .sort((left, right) => right.weight - left.weight)
    .slice(0, 4);
}

export function filterResultsByIntent(
  items: ScoredImageMatch[],
  activeIntent: string | null,
): ScoredImageMatch[] {
  if (!activeIntent) return items;
  return items.filter((item) => (
    item.matchedQueryConcepts ?? []
  ).some((match) => match.conceptName === activeIntent));
}

export function displayConceptName(value: string): string {
  return value.split('>').at(-1)?.trim() || value.trim();
}

export function searchIntentTitle(queryType?: string | null): string {
  if (queryType === 'exploratory_business_intent_search') return '你可能在找';
  if (queryType === 'multi_business_intent_search') return '本次需求同时涉及';
  return '本次识别到的卖点';
}

export function resultMatchExplanation(item: ScoredImageMatch): string {
  const explanations: string[] = [];
  const matchedConcept = item.matchedQueryConcepts?.[0];
  if (matchedConcept) {
    explanations.push(
      matchedConcept.relationRole === 'expresses'
        ? `主要表达“${matchedConcept.conceptName}”`
        : `可以支持“${matchedConcept.conceptName}”`,
    );
  }

  const assetPhrase = reasonValue(item.matchReasons, '卖点内素材独有话术命中：');
  const proofPoint = reasonValue(item.matchReasons, '证明点匹配：');
  if (proofPoint) explanations.push(`证明点：${proofPoint}`);
  if (assetPhrase) explanations.push(`素材独有话术命中：${assetPhrase}`);

  if (!assetPhrase) {
    const conceptPhrase = reasonValue(item.matchReasons, '概念搜索表达命中：');
    if (conceptPhrase) explanations.push(`卖点表达命中：${conceptPhrase}`);
  }

  if (explanations.length > 0) return explanations.slice(0, 3).join('；');
  if (item.matchReasons.includes('标题匹配')) return '素材名称与搜索需求一致';
  if (item.matchReasons.includes('图片摘要匹配')) return '素材内容与搜索需求一致';
  if (item.matchReasons.includes('素材语义匹配')) return '素材独有内容与搜索需求一致';
  return '与当前搜索需求相关';
}

function reasonValue(reasons: string[], prefix: string): string | null {
  const reason = reasons.find((item) => item.startsWith(prefix));
  return reason?.slice(prefix.length).trim() || null;
}
