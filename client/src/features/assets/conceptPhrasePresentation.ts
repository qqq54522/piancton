import type {
  AssetConceptLink,
  BusinessConcept,
  ConceptSearchPhrase,
} from '@client/src/types/api';

export function selectInheritedConcepts(
  links: AssetConceptLink[],
  concepts: BusinessConcept[],
): BusinessConcept[] {
  const inheritedIds = new Set(
    links
      .filter((link) => (
        link.origin === 'manual'
        && link.reviewStatus === 'accepted'
        && link.relationRole !== 'excludes'
      ))
      .map((link) => link.conceptId),
  );
  return concepts.filter((concept) => inheritedIds.has(concept.id));
}

export function isAuxiliaryKeyword(phrase: ConceptSearchPhrase): boolean {
  return [...phrase.phrase.replace(/\s/g, '')].length < 4;
}

export function splitAcceptedConceptPhrases(phrases: ConceptSearchPhrase[]) {
  const seen = new Set<string>();
  const accepted = phrases.filter((item) => {
    if (item.reviewStatus !== 'accepted') return false;
    const key = item.phrase.trim().toLocaleLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return {
    publicPhrases: accepted.filter((item) => !isAuxiliaryKeyword(item)),
    keywords: accepted.filter(isAuxiliaryKeyword),
  };
}
