import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react';
import { ChevronDown, ChevronRight, FolderClosed, Loader2, RotateCcw, Upload } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Button } from '@client/src/components/ui/button';
import { Select } from '@client/src/components/ui/select';
import { ROLE_SUBJECT, useAuth } from '@client/src/lib/auth';
import { useImageBrowser } from '@client/src/features/images/useImageBrowser';
import { useAnimatedGifPreview } from '@client/src/features/images/useAnimatedGifPreview';
import { useForYouImages } from '@client/src/features/images/useForYouImages';
import { takeImageHomeScroll } from '@client/src/features/images/searchNavigationState';
import type { BusinessConcept, BusinessFacetCatalog, ImageItem, TagWithCount } from '@client/src/types/api';
import { type ChannelFolder } from '@client/src/features/images/channelFolders';
import GlobalImageSearch from './GlobalImageSearch';
import AssetAgentWidget from './AssetAgentWidget';
import ImageGrid from './ImageGrid';
import SemanticSearchResult from './SemanticSearchResult';
import UploadDialog, { type UploadMode } from './UploadDialog';
import type { ImageChannelIntent } from './channelIntent';
import { channelValueIncludes } from './channelValue';

/** 桌面端设计师/管理员使用左侧导航栏，不再占用顶部高度 */
const APP_HEADER_HEIGHT = 0;
const HOME_CONTENT_TOP_GAP = 16;
const SEARCH_LOADING_MESSAGE_HEIGHT_REM = 1.25;
const SEARCH_LOADING_MESSAGE_INTERVAL_MS = 2400;
const SEARCH_LOADING_MESSAGES = [
  '我先把这句话拆成业务动作、目标结果和使用场景。',
  '正在对照卖点知识库，判断它属于哪个核心卖点。',
  '命中卖点后，会回到素材库取这个卖点下已确认的图片。',
] as const;

interface ImageHomeLocationState {
  browseChannel?: string;
  browseChannelIntent?: ImageChannelIntent | null;
  openUpload?: boolean;
  uploadMode?: UploadMode;
}

const ImageHome = () => {
  const auth = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [manualFilterOpen, setManualFilterOpen] = useState(false);
  const [agentPanelOpen, setAgentPanelOpen] = useState(() => window.innerWidth >= 1024);
  const [uploadMode, setUploadMode] = useState<UploadMode>('single');
  const animatedGifPreview = useAnimatedGifPreview();
  const consumedLocationStateKeyRef = useRef<string | null>(null);
  const stickyHeaderRef = useRef<HTMLDivElement>(null);
  const stickyHeaderHeight = useElementHeight(stickyHeaderRef);
  const isDesigner = !auth.isLoading && auth.ability.can('designer', ROLE_SUBJECT);
  const isBusiness = auth.user?.role === 'business';
  const {
    businessConcepts,
    businessSystems,
    businessFacets,
    folderCatalog,
    selectedFolderId,
    setSelectedFolderId,
    setUnfiledOnly,
    clearGlobalSearch,
    executeGlobalSearch,
    globalSearchImages,
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
    selectedSystemCode,
    selectConcept,
    selectProofPoint,
    selectSystem,
    semanticResult,
    setChannelIntentRefinement,
    setSelectedChannel,
    setSelectedScene,
    sentinelRef,
    setSortBy,
    setUploadOpen,
    sortBy,
    uploadOpen,
  } = useImageBrowser();
  useEffect(() => {
    const keepAgentDocked = () => {
      if (window.innerWidth >= 1024) setAgentPanelOpen(true);
    };
    window.addEventListener('resize', keepAgentDocked);
    return () => window.removeEventListener('resize', keepAgentDocked);
  }, []);
  const showingTypedSearch = globalSearchSource === 'typed' && (Boolean(semanticResult) || Boolean(globalSearchKeyword));
  const showingForYou = isBusiness
    && !showingTypedSearch
    && !hasManualSearchResult
    && !searchRefinements.channel
    && !searchRefinements.channelIntent;
  const forYou = useForYouImages(showingForYou);
  const manualFilteredImages = hasManualSearchResult
    ? globalSearchImages
    : showingForYou
    ? mergeImages(forYou.data?.items ?? [], images)
    : images;
  const browsingImages = filterBrowseImages(manualFilteredImages, searchRefinements);
  const showingFilteredEmptyState = images.length > 0 && browsingImages.length === 0;
  const browsingLoading = loading
    || (globalSearchLoading && !showingTypedSearch)
    || (showingForYou && forYou.isLoading);
  const searchUnavailable = Boolean(globalSearchError);
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
      if (isDesigner) {
        setUploadMode(locationState.uploadMode ?? 'single');
        setUploadOpen(true);
      }
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
    const openUpload = (event: Event) => {
      if (!isDesigner) return;
      const detail = (event as CustomEvent<{ mode?: UploadMode }>).detail;
      setUploadMode(detail?.mode ?? 'single');
      setUploadOpen(true);
    };
    window.addEventListener('piancton:open-upload', openUpload);
    return () => window.removeEventListener('piancton:open-upload', openUpload);
  }, [isDesigner, setUploadOpen]);

  return (
    <div className="pb-8">
      <div
        ref={stickyHeaderRef}
        className={`fixed right-0 top-0 z-40 border-b border-border/60 bg-white lg:right-[440px] ${!isBusiness ? 'left-20' : 'left-0'} px-4 py-3 sm:px-6 lg:px-8`}
      >
        <div className="mx-auto w-full max-w-[1920px]">
          <GlobalImageSearch
            refinementOptions={refinementOptions}
            refinements={searchRefinements}
            sortBy={sortBy}
            showBusinessAccount={isBusiness}
            manualFilterOpen={manualFilterOpen}
            animateGifPreview={animatedGifPreview.enabled}
            agentOpen={agentPanelOpen}
            onChannelChange={(channel) => {
              setSelectedChannel(channel);
              setManualFilterOpen(Boolean(channel));
            }}
            onSceneChange={setSelectedScene}
            onSortByChange={setSortBy}
            onManualFilterOpenChange={setManualFilterOpen}
            onAnimateGifPreviewChange={animatedGifPreview.setEnabled}
            onAgentOpenChange={setAgentPanelOpen}
          />
        </div>
      </div>

      <div className="w-full px-0" style={{ paddingTop: contentTopOffset }}>
        <div className="transition-[padding] duration-300 ease-out lg:pr-[440px]">
          <div className="flex items-start gap-0 max-sm:flex-col">
            <ManualFilterRail
              open={manualFilterOpen}
              isBusiness={isBusiness}
              stickyTop={headerTopOffset}
              selectedConceptCode={selectedConceptCode}
              selectedProofPointCode={selectedProofPointCode}
              selectedSystemCode={selectedSystemCode}
              businessSystems={businessSystems}
              businessConcepts={businessConcepts}
              businessFacets={businessFacets}
              channel={searchRefinements.channel}
              folders={folderCatalog.find((item) => item.name === searchRefinements.channel)?.folders ?? []}
              selectedFolderId={selectedFolderId}
              onFolderChange={(id) => { setSelectedFolderId(id); setUnfiledOnly(false); }}
              onSystemChange={selectSystem}
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
                  showBusinessAccount={isBusiness}
                  animateGifPreview={animatedGifPreview.enabled}
                  onClear={clearGlobalSearch}
                />
              ) : (
                <div>
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-lg font-medium">「{globalSearchKeyword}」的搜索结果</h2>
                    <Button variant="ghost" size="sm" onClick={clearGlobalSearch}>清除搜索</Button>
                  </div>
                  <ImageGrid
                    images={globalSearchImages}
                    animateGifPreview={animatedGifPreview.enabled}
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
                      interactionSource={showingForYou ? 'home_for_you' : undefined}
                      animateGifPreview={animatedGifPreview.enabled}
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
      </div>

      <UploadDialog
        initialMode={uploadMode}
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onSuccess={handleUploadSuccess}
      />
      <AssetAgentWidget
        open={agentPanelOpen}
        onOpenChange={(open) => { if (window.innerWidth < 1024) setAgentPanelOpen(open); }}
        topOffset={0}
        dockLocked
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

  useEffect(() => {
    const timer = window.setInterval(() => {
      setMessageIndex((current) => (current + 1) % SEARCH_LOADING_MESSAGES.length);
    }, SEARCH_LOADING_MESSAGE_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="flex min-h-[360px] items-start justify-center px-4 pt-12 sm:pt-16">
      <div
        className="w-full max-w-[760px] rounded-3xl border border-border/70 bg-card px-6 py-6 shadow-sm sm:px-8"
        role="status"
        aria-live="polite"
      >
        <div className="rounded-2xl bg-secondary/55 px-5 py-5">
          <div className="mb-4 flex items-center gap-2 text-sm font-medium text-foreground">
            <span className="inline-flex size-5 animate-pulse items-center justify-center rounded-full bg-foreground text-[10px] text-background">
              ✺
            </span>
            思考中...
          </div>
          <div className="border-l border-border pl-4 text-sm leading-7 text-foreground/82">
            <div className="h-5 overflow-hidden">
              <div
                className="transition-transform duration-500 ease-out"
                style={{ transform: `translateY(-${messageIndex * SEARCH_LOADING_MESSAGE_HEIGHT_REM}rem)` }}
              >
                {SEARCH_LOADING_MESSAGES.map((message) => (
                  <p key={message} className="h-5 whitespace-nowrap leading-5">{message}</p>
                ))}
              </div>
            </div>
            <p className="mt-2 text-foreground/64">
              这一步会先判断卖点，再返回对应素材，稍等一下就好。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

interface ManualFilterRailProps {
  open: boolean;
  isBusiness: boolean;
  stickyTop: number;
  selectedConceptCode: string | null;
  selectedProofPointCode: string | null;
  selectedSystemCode: string | null;
  businessSystems: TagWithCount[];
  businessConcepts: BusinessConcept[];
  businessFacets: BusinessFacetCatalog;
  channel: string;
  folders: ChannelFolder[];
  selectedFolderId: string | null;
  onFolderChange: (id: string | null) => void;
  onSystemChange: (value: string | null) => void;
  onConceptChange: (value: string | null) => void;
  onProofPointChange: (value: string | null) => void;
}

const ManualFilterRail = ({
  open,
  isBusiness,
  stickyTop,
  selectedConceptCode,
  selectedProofPointCode,
  selectedSystemCode,
  businessSystems,
  businessConcepts,
  businessFacets,
  channel,
  folders,
  selectedFolderId,
  onFolderChange,
  onSystemChange,
  onConceptChange,
  onProofPointChange,
}: ManualFilterRailProps) => {
  const [expandedFolderIds, setExpandedFolderIds] = useState<Set<string>>(new Set());
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

  useEffect(() => { setExpandedFolderIds(new Set()); }, [channel]);

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
          <div className="mb-5 flex items-center justify-between gap-2">
            <h2 className="text-base font-semibold">{channel ? '分类' : '业务卖点'}</h2>
          </div>
          {channel ? (
            <div className="space-y-1">
              {folders.length > 0 && folders.filter((folder) => !folder.parentId)
                .sort((a, b) => a.name.localeCompare(b.name, 'zh')).map((folder) => (
                  <ChannelFolderBranch key={folder.id} folder={folder} folders={folders}
                    selectedFolderId={selectedFolderId} expandedFolderIds={expandedFolderIds}
                    onSelect={onFolderChange}
                    onToggle={(id) => setExpandedFolderIds((current) => {
                      const next = new Set(current);
                      if (next.has(id)) next.delete(id); else next.add(id);
                      return next;
                    })} />
                ))}
              {!folders.length && <p className="px-3 py-4 text-xs text-muted-foreground">这个渠道还没有分类，全部图片仍可浏览。</p>}
            </div>
          ) : <div className="space-y-7">
            <label className="block">
              <span className="field-label">体系</span>
              <Select aria-label="按体系筛选" value={selectedSystemCode ?? ''}
                onChange={(event) => onSystemChange(event.target.value || null)}>
                <option value="">全部体系</option>
                {businessSystems.map((system) => <option key={system.code} value={system.code ?? ''}>{system.name}</option>)}
              </Select>
            </label>
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
          </div>}
        </div>
        {!channel && <div className="mt-auto flex items-center gap-3 border-t border-border/60 bg-white p-5">
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
        </div>}
      </div>
    </aside>
  );
};

function ChannelFolderBranch({ folder, folders, selectedFolderId, expandedFolderIds, onSelect, onToggle }: {
  folder: ChannelFolder;
  folders: ChannelFolder[];
  selectedFolderId: string | null;
  expandedFolderIds: Set<string>;
  onSelect: (id: string | null) => void;
  onToggle: (id: string) => void;
}) {
  const children = folders.filter((item) => item.parentId === folder.id).sort((a, b) => a.name.localeCompare(b.name, 'zh'));
  const expanded = expandedFolderIds.has(folder.id);
  const active = selectedFolderId === folder.id;
  return <div className="mb-1">
    <div className={`flex items-center rounded-xl transition-colors ${active ? 'bg-foreground text-background' : 'bg-secondary/70 hover:bg-secondary'}`}>
      <button type="button" onClick={() => { onSelect(folder.id); if (children.length && !expanded) onToggle(folder.id); }}
        className="flex min-w-0 flex-1 items-center gap-3 px-3 py-3 text-left text-sm font-semibold">
        <span className={`grid size-8 shrink-0 place-items-center rounded-lg ${active ? 'bg-white/15' : 'bg-white'}`}><FolderClosed className="size-4 opacity-75" /></span>
        <span className="min-w-0 flex-1 truncate">{folder.name}</span>
      </button>
      {children.length > 0 && <button type="button" aria-label={`${expanded ? '收起' : '展开'}${folder.name}的下级分类`}
        aria-expanded={expanded} onClick={() => onToggle(folder.id)} className="mr-2 rounded-lg p-1.5 hover:bg-black/10">
        {expanded ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
      </button>}
    </div>
    {children.length > 0 && expanded && <div className="ml-5 mt-1 space-y-1 border-l border-border/80 pl-3">
      {children.map((child) => <ChannelFolderBranch key={child.id} folder={child} folders={folders}
        selectedFolderId={selectedFolderId} expandedFolderIds={expandedFolderIds}
        onSelect={onSelect} onToggle={onToggle} />)}
    </div>}
  </div>;
}

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

function mergeImages(primary: ImageItem[], fallback: ImageItem[]): ImageItem[] {
  const seen = new Set<string>();
  return [...primary, ...fallback].filter((image) => {
    if (seen.has(image.id)) return false;
    seen.add(image.id);
    return true;
  });
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
