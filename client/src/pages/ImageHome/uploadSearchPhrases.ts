export const INITIAL_UPLOAD_SEARCH_PHRASE_LIMIT = 5;

export function normalizeExpectedSearchWords(values: string[]): string[] {
  return [...new Set(values.map((item) => item.trim()).filter(Boolean))]
    .slice(0, INITIAL_UPLOAD_SEARCH_PHRASE_LIMIT);
}
