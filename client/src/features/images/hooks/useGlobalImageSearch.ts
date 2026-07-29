import { useCallback, useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import * as imageApi from '@client/src/api/image';
import { systemFilters } from '@client/src/features/assets/assetPresentation';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import { useBusinessFacets } from '@client/src/features/assets/useBusinessFacets';
import {
  collectSearchRefinementOptions,
  EMPTY_SEARCH_REFINEMENTS,
  type SceneImageFilter,
} from '@client/src/pages/ImageHome/searchResultFilters';
import {
  understandImageChannelIntent,
  type ImageChannelIntent,
} from '@client/src/pages/ImageHome/channelIntent';
import {
  isChannelIntentInCatalog,
  useChannelIntentEntries,
} from '@client/src/pages/ImageHome/channelIntentCatalog';
import type {
  BusinessConcept,
  ImageItem,
  SemanticSearchResponse,
  TagWithCount,
} from '@client/src/types/api';

interface SearchResult {
  semantic: SemanticSearchResponse | null;
  images: ImageItem[];
  source: SearchResultSource;
}

type SearchResultSource = 'typed' | 'manual';

interface SearchBusinessFilters {
  systemCode: string | null;
  conceptCode: string | null;
  proofPointCode: string | null;
  evidencePointCode: string | null;
}

interface StoredSearchState extends SearchBusinessFilters {
  input: string;
  keyword: string;
  channel: string;
  channelIntent: ImageChannelIntent | null;
  scene: SceneImageFilter;
  result: SearchResult | null;
}

const SEARCH_STATE_KEY = 'piancton:image-search-state:v2';

export function useGlobalImageSearch({ allTags }: { allTags: TagWithCount[] }) {
  const [initial] = useState(readSearchState);
  const [globalSearchInput, setGlobalSearchInput] = useState(initial.input);
  const [globalSearchKeyword, setGlobalSearchKeyword] = useState(initial.keyword);
  const [selectedSystemCode, setSelectedSystemCode] = useState<string | null>(initial.systemCode);
  const [selectedConceptCode, setSelectedConceptCode] = useState<string | null>(initial.conceptCode);
  const [selectedProofPointCode, setSelectedProofPointCode] = useState<string | null>(initial.proofPointCode);
  const [selectedChannel, setSelectedChannel] = useState(initial.channel);
  const [channelIntent, setChannelIntent] = useState<ImageChannelIntent | null>(initial.channelIntent);
  const [selectedScene, setSelectedScene] = useState<SceneImageFilter>(initial.scene);
  const [searchResult, setSearchResult] = useState<SearchResult | null>(initial.result);
  const conceptsQuery = useBusinessConcepts();
  const facetsQuery = useBusinessFacets();
  const channelIntentEntries = useChannelIntentEntries();
  const concepts = useMemo(() => conceptsQuery.data ?? [], [conceptsQuery.data]);
  const facets = useMemo(
    () => facetsQuery.data ?? { proofPoints: [], evidencePoints: [] },
    [facetsQuery.data],
  );
  const systems = useMemo(() => systemFilters(allTags), [allTags]);

  const systemCodeForConcept = useCallback((conceptCode: string | null) => {
    const concept = concepts.find((item) => item.code === conceptCode);
    if (!concept) return null;
    const preferredLink = [...concept.systemLinks]
      .filter((link) => link.status === 'active')
      .sort((left, right) => right.weight - left.weight)[0];
    return systems.find((system) => system.id === preferredLink?.systemTagId)?.code ?? null;
  }, [concepts, systems]);

  const semanticSearch = useMutation({
    mutationFn: async (payload: {
      keyword: string;
      preserveSelectedFilters: boolean;
      source: SearchResultSource;
    } & SearchBusinessFilters): Promise<SearchResult> => {
      const semantic = await imageApi.semanticSearch({
        keyword: payload.keyword,
        limit: 12,
        systemCode: payload.systemCode,
        conceptCode: payload.conceptCode,
        proofPointCode: payload.proofPointCode,
        evidencePointCode: payload.evidencePointCode,
      });
      return {
        semantic,
        images: semantic.results.map((result) => result.image),
        source: payload.source,
      };
    },
    onSuccess: (result, payload) => {
      setSearchResult(result);
      if (!result.semantic) return;
      if (payload.preserveSelectedFilters) {
        setSelectedSystemCode(payload.systemCode);
        setSelectedConceptCode(payload.conceptCode);
        setSelectedProofPointCode(payload.proofPointCode);
        return;
      }
      const recognized = recognizedBusinessFilters(result.semantic, concepts, systemCodeForConcept);
      setSelectedConceptCode(payload.conceptCode ?? recognized.conceptCode);
      setSelectedProofPointCode(payload.proofPointCode ?? recognized.proofPointCode);
      setSelectedSystemCode(payload.systemCode ?? recognized.systemCode);
    },
    onError: () => {
      setSearchResult(null);
    },
  });
  const semanticResult = searchResult?.semantic ?? null;
  const refinementOptions = useMemo(
    () => collectSearchRefinementOptions(semanticResult?.results ?? []),
    [semanticResult],
  );
  const knownChannelValues = useMemo(
    () => new Set(channelIntentEntries.map((entry) => entry.value)),
    [channelIntentEntries],
  );
  const resetRefinements = useCallback(() => {
    setSelectedChannel(EMPTY_SEARCH_REFINEMENTS.channel);
    setChannelIntent(EMPTY_SEARCH_REFINEMENTS.channelIntent);
    setSelectedScene(EMPTY_SEARCH_REFINEMENTS.scene);
  }, []);

  const executeGlobalSearch = useCallback((
    value?: string,
    filters?: Partial<SearchBusinessFilters>,
  ) => {
    const nextKeyword = (value ?? globalSearchInput).trim();
    if (!nextKeyword) return;
    const startsNewQuery = filters === undefined && nextKeyword !== globalSearchKeyword;
    const nextFilters: SearchBusinessFilters = {
      systemCode: filters?.systemCode === undefined
        ? startsNewQuery ? null : selectedSystemCode
        : filters.systemCode,
      conceptCode: filters?.conceptCode === undefined
        ? startsNewQuery ? null : selectedConceptCode
        : filters.conceptCode,
      proofPointCode: filters?.proofPointCode === undefined
        ? startsNewQuery ? null : selectedProofPointCode
        : filters.proofPointCode,
      evidencePointCode: null,
    };
    setGlobalSearchInput(nextKeyword);
    setGlobalSearchKeyword(nextKeyword);
    setSearchResult(null);
    if (startsNewQuery) {
      setSelectedSystemCode(null);
      setSelectedConceptCode(null);
      setSelectedProofPointCode(null);
    }
    resetRefinements();
    const nextChannelIntent = understandImageChannelIntent(nextKeyword, channelIntentEntries);
    setChannelIntent(isChannelIntentInCatalog(nextChannelIntent, channelIntentEntries) ? nextChannelIntent : null);
    semanticSearch.mutate({
      keyword: nextKeyword,
      ...nextFilters,
      preserveSelectedFilters: filters !== undefined || !startsNewQuery,
      source: 'typed',
    });
  }, [
    globalSearchInput,
    globalSearchKeyword,
    channelIntentEntries,
    resetRefinements,
    selectedConceptCode,
    selectedProofPointCode,
    selectedSystemCode,
    semanticSearch,
  ]);

  const rerunWith = useCallback((filters: SearchBusinessFilters, fallbackKeyword?: string | null) => {
    const typedKeyword = globalSearchKeyword.trim();
    if (typedKeyword) {
      executeGlobalSearch(typedKeyword, filters);
      return;
    }
    const manualKeyword = fallbackKeyword?.trim();
    if (!manualKeyword) {
      setSearchResult(null);
      setGlobalSearchInput('');
      setGlobalSearchKeyword('');
      resetRefinements();
      semanticSearch.reset();
      return;
    }
    setGlobalSearchInput('');
    setGlobalSearchKeyword('');
    resetRefinements();
    semanticSearch.mutate({
      keyword: manualKeyword,
      ...filters,
      preserveSelectedFilters: true,
      source: 'manual',
    });
  }, [executeGlobalSearch, globalSearchKeyword, resetRefinements, semanticSearch]);

  const selectSystem = useCallback((systemCode: string | null) => {
    const filters = { systemCode, conceptCode: null, proofPointCode: null, evidencePointCode: null };
    const systemName = systems.find((system) => system.code === systemCode)?.name;
    setSelectedSystemCode(systemCode);
    setSelectedConceptCode(null);
    setSelectedProofPointCode(null);
    rerunWith(filters, systemName);
  }, [rerunWith, systems]);

  const selectConcept = useCallback((conceptCode: string | null) => {
    const concept = concepts.find((item) => item.code === conceptCode);
    const systemCode = conceptCode ? systemCodeForConcept(conceptCode) : null;
    const filters = { systemCode, conceptCode, proofPointCode: null, evidencePointCode: null };
    setSelectedSystemCode(systemCode);
    setSelectedConceptCode(conceptCode);
    setSelectedProofPointCode(null);
    rerunWith(filters, concept?.name);
  }, [concepts, rerunWith, systemCodeForConcept]);

  const selectProofPoint = useCallback((proofPointCode: string | null) => {
    const proof = facets.proofPoints.find((item) => item.code === proofPointCode);
    const conceptCode = proof?.conceptCode ?? selectedConceptCode;
    const concept = concepts.find((item) => item.code === conceptCode);
    const systemCode = systemCodeForConcept(conceptCode);
    const filters = { systemCode, conceptCode, proofPointCode, evidencePointCode: null };
    setSelectedSystemCode(systemCode);
    setSelectedConceptCode(conceptCode);
    setSelectedProofPointCode(proofPointCode);
    rerunWith(filters, proof?.name ?? concept?.name);
  }, [concepts, facets.proofPoints, rerunWith, selectedConceptCode, systemCodeForConcept]);

  const clearGlobalSearch = useCallback(() => {
    setGlobalSearchInput('');
    setGlobalSearchKeyword('');
    setSelectedSystemCode(null);
    setSelectedConceptCode(null);
    setSelectedProofPointCode(null);
    setSearchResult(null);
    resetRefinements();
    semanticSearch.reset();
    window.sessionStorage.removeItem(SEARCH_STATE_KEY);
  }, [resetRefinements, semanticSearch]);

  const setChannelIntentRefinement = useCallback((nextChannelIntent: ImageChannelIntent | null) => {
    setSelectedChannel('');
    setChannelIntent(nextChannelIntent);
  }, []);

  const selectChannelRefinement = useCallback((channel: string) => {
    setChannelIntent(null);
    setSelectedChannel(channel);
  }, []);

  useEffect(() => {
    if (channelIntent && !isChannelIntentInCatalog(channelIntent, channelIntentEntries)) {
      setChannelIntent(null);
    }
    if (selectedChannel && !knownChannelValues.has(selectedChannel)) {
      setSelectedChannel('');
    }
  }, [channelIntent, channelIntentEntries, knownChannelValues, selectedChannel]);

  useEffect(() => {
    const state: StoredSearchState = {
      input: globalSearchInput,
      keyword: globalSearchKeyword,
      systemCode: selectedSystemCode,
      conceptCode: selectedConceptCode,
      proofPointCode: selectedProofPointCode,
      evidencePointCode: null,
      channel: selectedChannel,
      channelIntent,
      scene: selectedScene,
      result: searchResult,
    };
    window.sessionStorage.setItem(SEARCH_STATE_KEY, JSON.stringify(state));
  }, [
    globalSearchInput,
    globalSearchKeyword,
    searchResult,
    channelIntent,
    selectedChannel,
    selectedConceptCode,
    selectedProofPointCode,
    selectedScene,
    selectedSystemCode,
  ]);

  return {
    businessConcepts: concepts,
    businessFacets: facets,
    clearGlobalSearch,
    executeGlobalSearch,
    globalSearchImages: searchResult?.images ?? [],
    globalSearchInput,
    globalSearchKeyword,
    globalSearchLoading: semanticSearch.isPending,
    globalSearchError: semanticSearch.isError,
    globalSearchSource: searchResult?.source ?? 'typed',
    hasManualSearchResult: searchResult?.source === 'manual',
    refinementOptions,
    searchRefinements: { channel: selectedChannel, channelIntent, scene: selectedScene },
    selectedConceptCode,
    selectedProofPointCode,
    selectedSystemCode,
    selectConcept,
    selectProofPoint,
    selectSystem,
    semanticResult,
    setChannelIntentRefinement,
    setGlobalSearchInput,
    setSelectedChannel: selectChannelRefinement,
    setSelectedScene,
    systems,
  };
}

function readSearchState(): StoredSearchState {
  const empty: StoredSearchState = {
    input: '',
    keyword: '',
    systemCode: null,
    conceptCode: null,
    proofPointCode: null,
    evidencePointCode: null,
    channel: '',
    channelIntent: null,
    scene: 'all',
    result: null,
  };
  try {
    const raw = window.sessionStorage.getItem(SEARCH_STATE_KEY);
    const parsed = raw ? { ...empty, ...JSON.parse(raw) as StoredSearchState } : empty;
    if (parsed.result && !parsed.result.source) {
      parsed.result = { ...parsed.result, source: 'typed' };
    }
    return parsed;
  } catch {
    return empty;
  }
}

function recognizedBusinessFilters(
  result: SemanticSearchResponse,
  concepts: BusinessConcept[],
  systemCodeForConcept: (code: string | null) => string | null,
): SearchBusinessFilters {
  const understanding = result.searchUnderstanding;
  const evidence = [...(understanding?.matchedEvidencePoints ?? [])]
    .sort((left, right) => right.weight - left.weight)[0];
  const proof = [...(understanding?.matchedProofPoints ?? [])]
    .sort((left, right) => right.weight - left.weight)[0];
  const namedConcept = [...(understanding?.matchedBusinessConcepts ?? [])]
    .sort((left, right) => right.weight - left.weight)
    .map((match) => match.concept.split('>').at(-1)?.trim() ?? match.concept.trim())
    .map((name) => concepts.find((concept) => concept.name === name)?.code)
    .find(Boolean);
  const conceptCode = evidence?.conceptCode ?? proof?.conceptCode ?? namedConcept ?? null;
  return {
    systemCode: systemCodeForConcept(conceptCode),
    conceptCode,
    proofPointCode: evidence?.proofPointCode ?? proof?.code ?? null,
    evidencePointCode: null,
  };
}
