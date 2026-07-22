import { useLayoutEffect } from 'react';
import { Loader2, Upload } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { ROLE_SUBJECT, useAuth } from '@client/src/lib/auth';
import { useImageBrowser } from '@client/src/features/images/useImageBrowser';
import { takeImageHomeScroll } from '@client/src/features/images/searchNavigationState';
import GlobalImageSearch from './GlobalImageSearch';
import ImageGrid from './ImageGrid';
import ImageHomeHeader from './ImageHomeHeader';
import LocalImageToolbar from './LocalImageToolbar';
import SemanticSearchResult from './SemanticSearchResult';
import UploadDialog from './UploadDialog';

const ImageHome = () => {
  const auth = useAuth();
  const isDesigner = !auth.isLoading && auth.ability.can('designer', ROLE_SUBJECT);
  const {
    businessConcepts,
    businessFacets,
    clearGlobalSearch,
    executeGlobalSearch,
    globalSearchImages,
    globalSearchInput,
    globalSearchKeyword,
    globalSearchLoading,
    handleUploadSuccess,
    hasMore,
    images,
    loading,
    loadingMore,
    refinementOptions,
    searchRefinements,
    selectedSystemCode,
    selectedConceptCode,
    selectedProofPointCode,
    selectedEvidencePointCode,
    selectConcept,
    selectProofPoint,
    selectEvidencePoint,
    selectSystem,
    semanticResult,
    setSelectedChannel,
    setSelectedScene,
    setSelectedStyle,
    sentinelRef,
    setGlobalSearchInput,
    setSortBy,
    setUploadOpen,
    sortBy,
    systems,
    uploadOpen,
  } = useImageBrowser();

  useLayoutEffect(() => {
    if (globalSearchLoading || loading) return;
    const scrollY = takeImageHomeScroll();
    if (scrollY === null) return;
    window.requestAnimationFrame(() => window.scrollTo({ top: scrollY }));
  }, [globalSearchLoading, loading]);

  return (
    <div className="page-shell">
      <ImageHomeHeader isDesigner={isDesigner} onOpenUpload={() => setUploadOpen(true)} />

      <GlobalImageSearch
        input={globalSearchInput}
        systems={systems}
        selectedSystemCode={selectedSystemCode}
        selectedConceptCode={selectedConceptCode}
        selectedProofPointCode={selectedProofPointCode}
        selectedEvidencePointCode={selectedEvidencePointCode}
        businessConcepts={businessConcepts}
        businessFacets={businessFacets}
        refinementOptions={refinementOptions}
        refinements={searchRefinements}
        refinementsReady={Boolean(semanticResult) && !globalSearchLoading}
        onInputChange={setGlobalSearchInput}
        onSystemChange={selectSystem}
        onConceptChange={selectConcept}
        onProofPointChange={selectProofPoint}
        onEvidencePointChange={selectEvidencePoint}
        onChannelChange={setSelectedChannel}
        onSceneChange={setSelectedScene}
        onStyleChange={setSelectedStyle}
        onClear={clearGlobalSearch}
        onSearch={executeGlobalSearch}
      />

      {globalSearchKeyword ? (
        globalSearchLoading ? (
          <div className="mt-6 flex flex-col items-center justify-center py-20">
            <Loader2 className="size-6 animate-spin text-primary" />
            <p className="mt-3 text-sm text-muted-foreground">正在搜索匹配素材...</p>
          </div>
        ) : semanticResult ? (
          <SemanticSearchResult
            keyword={globalSearchKeyword}
            result={semanticResult}
            refinements={searchRefinements}
            onClear={clearGlobalSearch}
          />
        ) : (
          <div className="mt-6">
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
        <>
          <LocalImageToolbar imageCount={images.length} sortBy={sortBy} onSortByChange={setSortBy} />
          <section className="mt-5">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="size-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                <ImageGrid
                  images={images}
                  emptyText="素材库还是空的"
                  emptyDescription={isDesigner
                    ? '上传第一张已审核主图，系统会自动建立素材组并开始分析。业务概念和延展尺寸都可以稍后补充。'
                    : '当前还没有已发布素材，请联系设计师或管理员完成首批素材录入。'}
                  emptyAction={isDesigner ? (
                    <Button onClick={() => setUploadOpen(true)}>
                      <Upload className="size-4" />上传第一张主图
                    </Button>
                  ) : undefined}
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
        </>
      )}

      <UploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onSuccess={handleUploadSuccess}
      />
    </div>
  );
};

export default ImageHome;
