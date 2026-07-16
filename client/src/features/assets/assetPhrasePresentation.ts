import type { AssetSearchPhrase } from '@client/src/types/api';

function normalizePhrase(phrase: string): string {
  return phrase.trim().toLocaleLowerCase();
}

export function splitAssetSearchPhrases(phrases: AssetSearchPhrase[]) {
  const acceptedKeys = new Set<string>();
  const accepted = phrases.filter((item) => {
    if (item.reviewStatus !== 'accepted') return false;
    const key = normalizePhrase(item.phrase);
    if (!key || acceptedKeys.has(key)) return false;
    acceptedKeys.add(key);
    return true;
  });
  const pendingAi = phrases.filter((item) => (
    item.origin === 'ai'
    && item.reviewStatus === 'pending'
    && !acceptedKeys.has(normalizePhrase(item.phrase))
  ));

  return { accepted, pendingAi };
}
