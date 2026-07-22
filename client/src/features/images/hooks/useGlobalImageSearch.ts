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
import type {
  BusinessConcept,
  ImageItem,
  SemanticSearchResponse,
  TagWithCount,
} from '@client/src/types/api';

interface SearchResult {
  semantic: SemanticSearchResponse | null;
  images: ImageItem[];
}

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
  style: string;
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
  const [selectedEvidencePointCode, setSelectedEvidencePointCode] = useState<string | null>(initial.evidencePointCode);
  const [selectedChannel, setSelectedChannel] = useState(initial.channel);
  const [selectedStyle, setSelectedStyle] = useState(initial.style);
  const [selectedScene, setSelectedScene] = useState<SceneImageFilter>(initial.scene);
  const [searchResult, setSearchResult] = useState<SearchResult | null>(initial.result);
  const conceptsQuery = useBusinessConcepts();
  const facetsQuery = useBusinessFacets();
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
    } & SearchBusinessFilters): Promise<SearchResult> => {
      try {
        const semantic = await imageApi.semanticSearch({
          keyword: payload.keyword,
          limit: 12,
          systemCode: payload.systemCode,
          conceptCode: payload.conceptCode,
          proofPointCode: payload.proofPointCode,
          evidencePointCode: payload.evidencePointCode,
        });
        return { semantic, images: semantic.results.map((result) => result.image) };
      } catch {
        const fallback = await imageApi.fetchImages({ keyword: payload.keyword, limit: 12 });
        return { semantic: null, images: fallback.items };
      }
    },
    onSuccess: (result, payload) => {
      setSearchResult(result);
      if (!result.semantic) return;
      if (payload.preserveSelectedFilters) {
        setSelectedSystemCode(payload.systemCode);
        setSelectedConceptCode(payload.conceptCode);
        setSelectedProofPointCode(payload.proofPointCode);
        setSelectedEvidencePointCode(payload.evidencePointCode);
        return;
      }
      const recognized = recognizedBusinessFilters(result.semantic, concepts, systemCodeForConcept);
      setSelectedConceptCode(payload.conceptCode ?? recognized.conceptCode);
      setSelectedProofPointCode(payload.proofPointCode ?? recognized.proofPointCode);
      setSelectedEvidencePointCode(payload.evidencePointCode ?? recognized.evidencePointCode);
      setSelectedSystemCode(payload.systemCode ?? recognized.systemCode);
    },
  });
  const semanticResult = searchResult?.semantic ?? null;
  const refinementOptions = useMemo(
    () => collectSearchRefinementOptions(semanticResult?.results ?? []),
    [semanticResult],
  );
  const resetRefinements = useCallback(() => {
    setSelectedChannel(EMPTY_SEARCH_REFINEMENTS.channel);
    setSelectedStyle(EMPTY_SEARCH_REFINEMENTS.style);
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
      evidencePointCode: filters?.evidencePointCode === undefined
        ? startsNewQuery ? null : selectedEvidencePointCode
        : filters.evidencePointCode,
    };
    setGlobalSearchInput(nextKeyword);
    setGlobalSearchKeyword(nextKeyword);
    if (startsNewQuery) {
      setSelectedSystemCode(null);
      setSelectedConceptCode(null);
      setSelectedProofPointCode(null);
      setSelectedEvidencePointCode(null);
    }
    resetRefinements();
    semanticSearch.mutate({
      keyword: nextKeyword,
      ...nextFilters,
      preserveSelectedFilters: filters !== undefined || !startsNewQuery,
    });
  }, [
    globalSearchInput,
    globalSearchKeyword,
    resetRefinements,
    selectedConceptCode,
    selectedEvidencePointCode,
    selectedProofPointCode,
    selectedSystemCode,
    semanticSearch,
  ]);

  const rerunWith = useCallback((filters: SearchBusinessFilters) => {
    if (globalSearchKeyword) executeGlobalSearch(globalSearchKeyword, filters);
  }, [executeGlobalSearch, globalSearchKeyword]);

  const selectSystem = useCallback((systemCode: string | null) => {
    const filters = { systemCode, conceptCode: null, proofPointCode: null, evidencePointCode: null };
    setSelectedSystemCode(systemCode);
    setSelectedConceptCode(null);
    setSelectedProofPointCode(null);
    setSelectedEvidencePointCode(null);
    rerunWith(filters);
  }, [rerunWith]);

  const selectConcept = useCallback((conceptCode: string | null) => {
    const systemCode = conceptCode ? systemCodeForConcept(conceptCode) : selectedSystemCode;
    const filters = { systemCode, conceptCode, proofPointCode: null, evidencePointCode: null };
    setSelectedSystemCode(systemCode);
    setSelectedConceptCode(conceptCode);
    setSelectedProofPointCode(null);
    setSelectedEvidencePointCode(null);
    rerunWith(filters);
  }, [rerunWith, selectedSystemCode, systemCodeForConcept]);

  const selectProofPoint = useCallback((proofPointCode: string | null) => {
    const proof = facets.proofPoints.find((item) => item.code === proofPointCode);
    const conceptCode = proof?.conceptCode ?? selectedConceptCode;
    const systemCode = systemCodeForConcept(conceptCode);
    const filters = { systemCode, conceptCode, proofPointCode, evidencePointCode: null };
    setSelectedSystemCode(systemCode);
    setSelectedConceptCode(conceptCode);
    setSelectedProofPointCode(proofPointCode);
    setSelectedEvidencePointCode(null);
    rerunWith(filters);
  }, [facets.proofPoints, rerunWith, selectedConceptCode, systemCodeForConcept]);

  const selectEvidencePoint = useCallback((evidencePointCode: string | null) => {
    const evidence = facets.evidencePoints.find((item) => item.code === evidencePointCode);
    const proofPointCode = evidence?.proofPointCode ?? selectedProofPointCode;
    const conceptCode = evidence?.conceptCode ?? selectedConceptCode;
    const systemCode = systemCodeForConcept(conceptCode);
    const filters = { systemCode, conceptCode, proofPointCode, evidencePointCode };
    setSelectedSystemCode(systemCode);
    setSelectedConceptCode(conceptCode);
    setSelectedProofPointCode(proofPointCode);
    setSelectedEvidencePointCode(evidencePointCode);
    rerunWith(filters);
  }, [
    facets.evidencePoints,
    rerunWith,
    selectedConceptCode,
    selectedProofPointCode,
    systemCodeForConcept,
  ]);

  const clearGlobalSearch = useCallback(() => {
    setGlobalSearchInput('');
    setGlobalSearchKeyword('');
    setSelectedSystemCode(null);
    setSelectedConceptCode(null);
    setSelectedProofPointCode(null);
    setSelectedEvidencePointCode(null);
    setSearchResult(null);
    resetRefinements();
    semanticSearch.reset();
    window.sessionStorage.removeItem(SEARCH_STATE_KEY);
  }, [resetRefinements, semanticSearch]);

  useEffect(() => {
    const state: StoredSearchState = {
      input: globalSearchInput,
      keyword: globalSearchKeyword,
      systemCode: selectedSystemCode,
      conceptCode: selectedConceptCode,
      proofPointCode: selectedProofPointCode,
      evidencePointCode: selectedEvidencePointCode,
      channel: selectedChannel,
      style: selectedStyle,
      scene: selectedScene,
      result: searchResult,
    };
    window.sessionStorage.setItem(SEARCH_STATE_KEY, JSON.stringify(state));
  }, [
    globalSearchInput,
    globalSearchKeyword,
    searchResult,
    selectedChannel,
    selectedConceptCode,
    selectedEvidencePointCode,
    selectedProofPointCode,
    selectedScene,
    selectedStyle,
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
    refinementOptions,
    searchRefinements: { channel: selectedChannel, style: selectedStyle, scene: selectedScene },
    selectedConceptCode,
    selectedEvidencePointCode,
    selectedProofPointCode,
    selectedSystemCode,
    selectConcept,
    selectEvidencePoint,
    selectProofPoint,
    selectSystem,
    semanticResult,
    setGlobalSearchInput,
    setSelectedChannel,
    setSelectedScene,
    setSelectedStyle,
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
    style: '',
    scene: 'all',
    result: null,
  };
  try {
    const raw = window.sessionStorage.getItem(SEARCH_STATE_KEY);
    return raw ? { ...empty, ...JSON.parse(raw) as StoredSearchState } : empty;
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
    evidencePointCode: evidence?.code ?? null,
  };
}
