import { useMutation } from '@tanstack/react-query';

import { generateAssetSearchPhrases } from '@client/src/api/image';


export function useAssetPhraseSuggestions() {
  return useMutation({ mutationFn: generateAssetSearchPhrases });
}
