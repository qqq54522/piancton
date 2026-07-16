import type {
  ScoredImageMatch,
  SearchUnderstanding,
} from '@client/src/types/api';

export interface SearchIntentOption {
  name: string;
  weight: number;
}

export function searchIntentOptions(
  understanding?: SearchUnderstanding,
): SearchIntentOption[] {
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
