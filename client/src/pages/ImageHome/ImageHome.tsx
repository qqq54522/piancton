import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react';
import { Loader2, RotateCcw, Upload } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Button } from '@client/src/components/ui/button';
import { Select } from '@client/src/components/ui/select';
import { ROLE_SUBJECT, useAuth } from '@client/src/lib/auth';
import { useImageBrowser } from '@client/src/features/images/useImageBrowser';
import { takeImageHomeScroll } from '@client/src/features/images/searchNavigationState';
import type { BusinessConcept, BusinessFacetCatalog, ImageItem } from '@client/src/types/api';
import GlobalImageSearch from './GlobalImageSearch';
import ImageGrid from './ImageGrid';
import SemanticSearchResult from './SemanticSearchResult';
import UploadDialog from './UploadDialog';
import type { ImageChannelIntent } from './channelIntent';
import { channelValueIncludes } from './channelValue';

/** 桌面端设计师/管理员使用左侧导航栏，不再占用顶部高度 */
const APP_HEADER_HEIGHT = 0;
const HOME_CONTENT_TOP_GAP = 16;
const SEARCH_LOADING_ESTIMATE_MS = 60_000;
const SEARCH_LOADING_MESSAGE_HEIGHT_REM = 1.25;
const SEARCH_LOADING_MESSAGE_INTERVAL_MS = 2400;
const SEARCH_LOADING_PROGRESS_TICK_MS = 500;
const SEARCH_LOADING_PROGRESS_RADIUS = 34;
const SEARCH_LOADING_PROGRESS_CIRCUMFERENCE = 2 * Math.PI * SEARCH_LOADING_PROGRESS_RADIUS;
const SEARCH_LOADING_MESSAGES = [
  '搜索时间较长，预计 20-60 秒，请耐心等待',
  '正在进行语义匹配，结果会自动出现',
] as const;

interface ImageHomeLocationState {
  browseChannel?: string;
  browseChannelIntent?: ImageChannelIntent | null;
  openUpload?: boolean;
}

const ImageHome = () => {
  const auth = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [manualFilterOpen, setManualFilterOpen] = useState(false);
  const consumedLocationStateKeyRef = useRef<string | null>(null);
  const stickyHeaderRef = useRef<HTMLDivElement>(null);
  const stickyHeaderHeight = useElementHeight(stickyHeaderRef);
  const isDesigner = !auth.isLoading && auth.ability.can('designer', ROLE_SUBJECT);
  const isBusiness = auth.user?.role === 'business';
  const {
    businessConcepts,
    businessFacets,
    clearGlobalSearch,
    executeGlobalSearch,
    globalSearchImages,
    globalSearchInput,
    globalSearchKeyword,
    globalSearchError,
    globalSearchLoading,
    globalSearchSource,
    hasManualSearchResult,
    handleUploadSuccess,
    hasMore,
    images,
    loading,
    loadingMore,
    refinementOptions,
    searchRefinements,
    selectedConceptCode,
    selectedProofPointCode,
    selectConcept,
    selectProofPoint,
    semanticResult,
    setChannelIntentRefinement,
    setSelectedChannel,
    setSelectedScene,
    sentinelRef,
    setGlobalSearchInput,
    setSortBy,
    setUploadOpen,
    sortBy,
    uploadOpen,
  } = useImageBrowser();
  const showingTypedSearch = globalSearchSource === 'typed' && (Boolean(semanticResult) || Boolean(globalSearchKeyword));
  const manualFilteredImages = hasManualSearchResult
    ? globalSearchImages
    : images;
  const browsingImages = filterBrowseImages(manualFilteredImages, searchRefinements);
  const showingFilteredEmptyState = images.length > 0 && browsingImages.length === 0;
  const browsingLoading = loading || (globalSearchLoading && !showingTypedSearch);
  const searchUnavailable = globalSearchError || Boolean(semanticResult?.fallback);
  const headerTopOffset = (isBusiness ? 0 : APP_HEADER_HEIGHT) + stickyHeaderHeight;
  const contentTopOffset = headerTopOffset + HOME_CONTENT_TOP_GAP;
  const retrySearch = () => {
    if (globalSearchKeyword.trim()) {
      executeGlobalSearch(globalSearchKeyword);
      return;
    }
    if (selectedProofPointCode) {
      selectProofPoint(selectedProofPointCode);
      return;
    }
    if (selectedConceptCode) {
      selectConcept(selectedConceptCode);
    }
  };

  useLayoutEffect(() => {
    if (globalSearchLoading || loading) return;
    const scrollY = takeImageHomeScroll();
    if (scrollY === null) return;
    let firstFrame = 0;
    let secondFrame = 0;
    firstFrame = window.requestAnimationFrame(() => {
      secondFrame = window.requestAnimationFrame(() => {
        window.scrollTo({ top: scrollY });
      });
    });
    return () => {
      window.cancelAnimationFrame(firstFrame);
      window.cancelAnimationFrame(secondFrame);
    };
  }, [globalSearchLoading, loading]);

  useEffect(() => {
    const locationState = location.state as ImageHomeLocationState | null;
    if (!locationState) return;
    const stateKey = location.key;
    if (consumedLocationStateKeyRef.current === stateKey) return;
    consumedLocationStateKeyRef.current = stateKey;

    let consumedState = false;
    if (locationState.openUpload) {
      if (isDesigner) setUploadOpen(true);
      consumedState = true;
    }

    const browseChannel = locationState.browseChannel?.trim() ?? '';
    const browseChannelIntent = locationState.browseChannelIntent ?? null;
    if (browseChannel || browseChannelIntent?.candidateChannels.length) {
      clearGlobalSearch();
      setManualFilterOpen(false);
      if (browseChannel) {
        setSelectedChannel(browseChannel);
      } else {
        setChannelIntentRefinement(browseChannelIntent);
      }
      window.requestAnimationFrame(() => window.scrollTo({ top: 0 }));
      consumedState = true;
    }

    if (consumedState) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [
    clearGlobalSearch,
    isDesigner,
    location.key,
    location.pathname,
    location.state,
    navigate,
    setChannelIntentRefinement,
    setSelectedChannel,
    setUploadOpen,
  ]);

  useEffect(() => {
    const openUpload = () => {
      if (isDesigner) setUploadOpen(true);
    };
    window.addEventListener('piancton:open-upload', openUpload);
    return () => window.removeEventListener('piancton:open-upload', openUpload);
  }, [isDesigner, setUploadOpen]);

  return (
    <div className="pb-8">
      <div
        ref={stickyHeaderRef}
        className={`fixed right-0 top-0 z-40 border-b border-border/60 bg-white ${!isBusiness ? 'left-20' : 'left-0'} ${isBusiness ? 'px-4 py-4 sm:px-6 lg:px-8' : 'px-4 pb-4 pt-3 sm:px-6 lg:px-8'}`}
      >
        <div className="mx-auto w-full max-w-[1920px]">
          <GlobalImageSearch
            input={globalSearchInput}
            refinementOptions={refinementOptions}
            refinements={searchRefinements}
            refinementsReady={Boolean(semanticResult) && !globalSearchLoading}
            sortBy={sortBy}
            showBusinessAccount={isBusiness}
            manualFilterOpen={manualFilterOpen}
            onInputChange={setGlobalSearchInput}
            onChannelChange={setSelectedChannel}
            onSceneChange={setSelectedScene}
            onSortByChange={setSortBy}
            onManualFilterOpenChange={setManualFilterOpen}
            onClear={clearGlobalSearch}
            onSearch={executeGlobalSearch}
          />
        </div>
      </div>

      <div className="w-full px-0" style={{ paddingTop: contentTopOffset }}>
        <div className="flex items-start gap-0 max-sm:flex-col">
          <ManualFilterRail
            open={manualFilterOpen}
            isBusiness={isBusiness}
            stickyTop={headerTopOffset}
            selectedConceptCode={selectedConceptCode}
            selectedProofPointCode={selectedProofPointCode}
            businessConcepts={businessConcepts}
            businessFacets={businessFacets}
            onConceptChange={selectConcept}
            onProofPointChange={selectProofPoint}
          />
          <div className={`min-w-0 flex-1 px-4 transition-[margin] duration-300 sm:px-6 lg:px-8 ${manualFilterOpen ? 'sm:ml-[320px]' : ''}`}>
            {searchUnavailable ? (
              <SearchErrorState
                canRetry={Boolean(globalSearchKeyword || selectedConceptCode || selectedProofPointCode)}
                onClear={clearGlobalSearch}
                onRetry={retrySearch}
              />
            ) : showingTypedSearch ? (
              globalSearchLoading ? (
                <SearchLoadingState />
              ) : semanticResult ? (
                <SemanticSearchResult
                  keyword={globalSearchKeyword || '手动筛选'}
                  result={semanticResult}
                  refinements={searchRefinements}
                  showSearchContext={globalSearchSource === 'typed'}
                  manualFilterOpen={manualFilterOpen}
                  showBusinessAccount={isBusiness}
                  onClear={clearGlobalSearch}
                  onRetry={retrySearch}
                />
              ) : (
                <div>
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-lg font-medium">「{globalSearchKeyword}」的搜索结果</h2>
                    <Button variant="ghost" size="sm" onClick={clearGlobalSearch}>清除搜索</Button>
                  </div>
                  <ImageGrid
                    images={globalSearchImages}
                    emptyText="暂时没有匹配素材"
                    emptyDescription="可以换一种业务说法、清除体系筛选，或在素材详情补充新的搜索话术。"
                  />
                </div>
              )
            ) : (
              <section>
                {browsingLoading ? (
                  <div className="flex items-center justify-center py-20">
                    <Loader2 className="size-6 animate-spin text-muted-foreground" />
                  </div>
                ) : (
                  <>
                    <ImageGrid
                      images={browsingImages}
                      emptyText={showingFilteredEmptyState ? '暂时还没有素材哦' : hasManualSearchResult ? '暂时没有找到合适素材' : '素材库还是空的'}
                      emptyDescription={showingFilteredEmptyState
                        ? undefined
                        : hasManualSearchResult
                        ? '可以换一个卖点或切回全部卖点继续浏览。'
                        : isDesigner
                        ? '上传第一张已审核主图，系统会自动建立素材组并开始分析。业务概念和延展尺寸都可以稍后补充。'
                        : '当前还没有已发布素材，请联系设计师或管理员完成首批素材录入。'}
                      emptyAction={!showingFilteredEmptyState && !hasManualSearchResult && isDesigner ? (
                        <Button className="bg-foreground text-background hover:bg-foreground/88" onClick={() => setUploadOpen(true)}>
                          <Upload className="size-4" />上传第一张主图
                        </Button>
                      ) : undefined}
                      emptyVariant={showingFilteredEmptyState ? 'plain' : 'card'}
                      layout="masonry"
                      withPresence
                    />
                    <div ref={sentinelRef} className="mt-4 flex justify-center py-4">
                      {loadingMore && <Loader2 className="size-5 animate-spin text-muted-foreground" />}
                      {!hasMore && images.length > 0 && (
                        <p className="text-xs text-muted-foreground">没有更多了</p>
                      )}
                    </div>
                  </>
                )}
              </section>
            )}
          </div>
        </div>
      </div>

      <UploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onSuccess={handleUploadSuccess}
      />
    </div>
  );
};

const SearchErrorState = ({
  canRetry,
  onClear,
  onRetry,
}: {
  canRetry: boolean;
  onClear: () => void;
  onRetry: () => void;
}) => (
  <div className="flex min-h-[360px] items-center justify-center">
    <div className="text-center">
      <h2 className="text-base font-semibold text-muted-foreground">查找通道出现了一些问题，请稍后再试</h2>
      <div className="mt-4 flex items-center justify-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
          disabled={!canRetry}
          onClick={onRetry}
        >
          <RotateCcw className="size-4" />
          重新尝试
        </Button>
        <Button type="button" variant="ghost" size="sm" className="rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground" onClick={onClear}>
          清除搜索
        </Button>
      </div>
    </div>
  </div>
);

const SearchLoadingState = () => {
  const [messageIndex, setMessageIndex] = useState(0);
  const [progress, setProgress] = useState(() => getEstimatedSearchProgress(0));

  useEffect(() => {
    const timer = window.setInterval(() => {
      setMessageIndex((current) => (current + 1) % SEARCH_LOADING_MESSAGES.length);
    }, SEARCH_LOADING_MESSAGE_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const startedAt = performance.now();
    const updateProgress = () => {
      setProgress(getEstimatedSearchProgress(performance.now() - startedAt));
    };
    updateProgress();
    const timer = window.setInterval(updateProgress, SEARCH_LOADING_PROGRESS_TICK_MS);
    return () => window.clearInterval(timer);
  }, []);

  const strokeDashoffset = SEARCH_LOADING_PROGRESS_CIRCUMFERENCE
    * (1 - progress / 100);

  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div
        className="relative size-24"
        role="progressbar"
        aria-label="搜索进度"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress}
      >
        <svg className="size-24 -rotate-90" viewBox="0 0 80 80" aria-hidden="true">
          <circle
            className="stroke-secondary"
            cx="40"
            cy="40"
            r={SEARCH_LOADING_PROGRESS_RADIUS}
            fill="none"
            strokeWidth="6"
          />
          <circle
            className="stroke-foreground transition-[stroke-dashoffset] duration-500 ease-out"
            cx="40"
            cy="40"
            r={SEARCH_LOADING_PROGRESS_RADIUS}
            fill="none"
            strokeLinecap="round"
            strokeWidth="6"
            style={{
              strokeDasharray: SEARCH_LOADING_PROGRESS_CIRCUMFERENCE,
              strokeDashoffset,
            }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-base font-semibold text-foreground">
          {progress}%
        </span>
      </div>
      <div className="mt-4 h-5 max-w-[90vw] overflow-hidden text-center text-sm text-muted-foreground" aria-live="polite">
        <div
          className="transition-transform duration-500 ease-out"
          style={{ transform: `translateY(-${messageIndex * SEARCH_LOADING_MESSAGE_HEIGHT_REM}rem)` }}
        >
          {SEARCH_LOADING_MESSAGES.map((message) => (
            <p key={message} className="h-5 whitespace-nowrap leading-5">{message}</p>
          ))}
        </div>
      </div>
    </div>
  );
};

function getEstimatedSearchProgress(elapsedMs: number): number {
  const earlyProgress = Math.min(elapsedMs / SEARCH_LOADING_ESTIMATE_MS, 1);
  const easedProgress = 1 - Math.pow(1 - earlyProgress, 2.4);
  if (elapsedMs <= SEARCH_LOADING_ESTIMATE_MS) {
    return Math.round(8 + easedProgress * 84);
  }
  const longWaitProgress = Math.min((elapsedMs - SEARCH_LOADING_ESTIMATE_MS) / SEARCH_LOADING_ESTIMATE_MS, 1);
  return Math.round(92 + longWaitProgress * 4);
}

interface ManualFilterRailProps {
  open: boolean;
  isBusiness: boolean;
  stickyTop: number;
  selectedConceptCode: string | null;
  selectedProofPointCode: string | null;
  businessConcepts: BusinessConcept[];
  businessFacets: BusinessFacetCatalog;
  onConceptChange: (value: string | null) => void;
  onProofPointChange: (value: string | null) => void;
}

const ManualFilterRail = ({
  open,
  isBusiness,
  stickyTop,
  selectedConceptCode,
  selectedProofPointCode,
  businessConcepts,
  businessFacets,
  onConceptChange,
  onProofPointChange,
}: ManualFilterRailProps) => {
  const [draftConceptCode, setDraftConceptCode] = useState<string | null>(selectedConceptCode);
  const [draftProofPointCode, setDraftProofPointCode] = useState<string | null>(selectedProofPointCode);
  const visibleProofPoints = businessFacets.proofPoints.filter(
    (point) => point.conceptCode === draftConceptCode,
  );
  const hasChanges = draftConceptCode !== selectedConceptCode
    || draftProofPointCode !== selectedProofPointCode;
  const hasAnyFilter = Boolean(
    draftConceptCode
    || draftProofPointCode
    || selectedConceptCode
    || selectedProofPointCode,
  );

  useEffect(() => {
    if (!open) return;
    setDraftConceptCode(selectedConceptCode);
    setDraftProofPointCode(selectedProofPointCode);
  }, [open, selectedConceptCode, selectedProofPointCode]);

  const handleConceptDraftChange = (value: string | null) => {
    setDraftConceptCode(value);
    setDraftProofPointCode(null);
  };

  const handleApply = () => {
    if (draftProofPointCode) {
      onProofPointChange(draftProofPointCode);
      return;
    }
    onConceptChange(draftConceptCode);
  };

  const handleResetDraft = () => {
    setDraftConceptCode(null);
    setDraftProofPointCode(null);
    if (selectedConceptCode || selectedProofPointCode) {
      onConceptChange(null);
    }
  };

  return (
    <aside
      aria-hidden={!open}
      style={{ top: stickyTop, height: `calc(100dvh - ${stickyTop}px)` }}
      className={`shrink-0 self-start overflow-hidden transition-[width,opacity,margin] duration-300 ease-out sm:fixed sm:z-30 max-sm:!static max-sm:!h-auto max-sm:w-full ${isBusiness ? 'sm:left-0' : 'sm:left-20'} ${open ? 'w-[320px] opacity-100 max-sm:mb-4' : 'w-0 opacity-0 max-sm:hidden'}`}
    >
      <div className="flex h-full max-h-full w-[320px] flex-col border-r border-border/70 bg-white max-sm:w-full max-sm:rounded-[24px] max-sm:border">
        <div className="min-h-0 overflow-y-auto px-7 py-7 compact-scrollbar max-sm:px-5 max-sm:py-5">
          <div className="space-y-7">
            <label className="block">
              <span className="field-label">卖点</span>
              <Select
                aria-label="按卖点筛选"
                value={draftConceptCode ?? ''}
                onChange={(event) => handleConceptDraftChange(event.target.value || null)}
              >
                <option value="">全部卖点</option>
                {businessConcepts.map((concept) => (
                  <option key={concept.code} value={concept.code}>{concept.name}</option>
                ))}
              </Select>
            </label>
            <label className="block">
              <span className="field-label">证明点</span>
              <Select
                aria-label="按证明点筛选"
                value={draftProofPointCode ?? ''}
                disabled={!draftConceptCode}
                onChange={(event) => setDraftProofPointCode(event.target.value || null)}
              >
                <option value="">全部证明点</option>
                {visibleProofPoints.map((point) => (
                  <option key={point.code} value={point.code}>{point.name}</option>
                ))}
              </Select>
            </label>
          </div>
        </div>
        <div className="mt-auto flex items-center gap-3 border-t border-border/60 bg-white p-5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="flex-1 rounded-full bg-white"
            onClick={handleResetDraft}
            disabled={!hasAnyFilter}
          >
            重置
          </Button>
          <Button
            type="button"
            size="sm"
            className="flex-1 rounded-full bg-foreground text-background hover:bg-foreground/88"
            onClick={handleApply}
            disabled={!hasChanges}
          >
            应用
          </Button>
        </div>
      </div>
    </aside>
  );
};

/** 读取 sticky 搜索区实际高度，供左侧筛选栏计算自身吸顶位置和最大高度 */
function useElementHeight(ref: RefObject<HTMLElement | null>): number {
  const [height, setHeight] = useState(0);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      setHeight(entry.target.getBoundingClientRect().height);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);

  return height;
}

function filterBrowseImages(
  images: ImageItem[],
  refinements: {
    channel: string;
    channelIntent: { candidateChannels: string[] } | null;
    scene: 'all' | 'scene' | 'nonScene';
  },
) {
  const intentChannels = refinements.channel
    ? []
    : refinements.channelIntent?.candidateChannels ?? [];
  return images.filter((image) => {
    if (refinements.channel && !channelValueIncludes(image.channel, refinements.channel)) return false;
    if (
      !refinements.channel
      && intentChannels.length > 0
      && !intentChannels.some((channel) => channelValueIncludes(image.channel, channel))
    ) return false;
    if (refinements.scene === 'scene' && image.isSceneImage !== true) return false;
    if (refinements.scene === 'nonScene' && image.isSceneImage !== false) return false;
    return true;
  });
}

export default ImageHome;
