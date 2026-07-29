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
  const recommendation = item.matchedQueryConcepts?.[0]?.recommendationText?.trim();
  if (recommendation) return recommendation;
  if (item.primaryProofPointClaim) return item.primaryProofPointClaim;
  const proofPointTitle = item.primaryProofPointName
    ?? cleanReasonText(reasonValue(item.matchReasons, '证明点匹配：') ?? '');
  const proofPointClaim = fallbackProofPointClaim(proofPointTitle);
  if (proofPointClaim) return proofPointClaim;
  const assetPhrase = reasonValue(item.matchReasons, '卖点内素材独有话术命中：');
  if (assetPhrase) return cleanReasonText(assetPhrase);
  if (proofPointTitle) return proofPointTitle;
  const conceptPhrase = reasonValue(item.matchReasons, '概念搜索表达命中：');
  if (conceptPhrase) return cleanReasonText(conceptPhrase);
  if (item.matchReasons.includes('标题匹配')) return '素材名称与搜索需求一致';
  if (item.matchReasons.includes('图片摘要匹配')) return '素材内容与搜索需求一致';
  if (item.matchReasons.includes('素材语义匹配')) return '素材独有内容与搜索需求一致';
  return '与当前搜索需求相关';
}

export interface ResultRecommendationCopy {
  primary: string;
  secondary: string[];
}

export function resultRecommendationCopy(item: ScoredImageMatch): ResultRecommendationCopy {
  const lines = resultMatchExplanation(item)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  return {
    primary: lines[0] ?? '与当前搜索需求相关',
    secondary: lines.slice(1),
  };
}

export function resultRecommendedPoint(item: ScoredImageMatch): string {
  const proofPointReason = cleanReasonText(reasonValue(item.matchReasons, '证明点匹配：') ?? '');
  return item.matchedQueryConcepts?.[0]?.conceptName
    ?? item.primaryProofPointName
    ?? item.primaryEvidencePointName
    ?? (proofPointReason || null)
    ?? '当前需求';
}

function reasonValue(reasons: string[], prefix: string): string | null {
  const reason = reasons.find((item) => item.startsWith(prefix));
  return reason?.slice(prefix.length).trim() || null;
}

function cleanReasonText(value: string): string {
  return value
    .replace(/[（(]\d+%[）)]/g, '')
    .replace(/^(主要表达|可以支持|证明点|素材独有话术命中|卖点表达命中)[：:]\s*/, '')
    .trim();
}

function fallbackProofPointClaim(name: string | null | undefined): string | null {
  if (!name) return null;
  const claims: Record<string, string> = {
    全网与群体高频易错题功能: '依托上亿学生答题数据，系统自动标记全学科高频易错题，区分共性易错坑点；同时内置个人专属错题本，自动收录孩子自身错题。',
    '同步动画课：先原理，后题型': '5-8 分钟单节动画课，先讲清底层原理，再延伸到不同题型和变式训练，让孩子更容易理解知识点。',
  };
  return claims[name] ?? null;
}
