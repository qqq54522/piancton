import { Loader2 } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { ROLE_SUBJECT, useAuth } from '@client/src/lib/auth';
import { useImageBrowser } from '@client/src/features/images/useImageBrowser';
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
    clearGlobalSearch,
    executeGlobalSearch,
    globalSearchImages,
    globalSearchInput,
    globalSearchKeyword,
    globalSearchLoading,
    handleUploadSuccess,
    hasMore,
    images,
    keyword,
    loading,
    loadingMore,
    searchInput,
    selectedSystemCode,
    selectSystem,
    semanticResult,
    sentinelRef,
    setGlobalSearchInput,
    setKeyword,
    setSearchInput,
    setSortBy,
    setUploadOpen,
    sortBy,
    systems,
    uploadOpen,
  } = useImageBrowser();

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <ImageHomeHeader isDesigner={isDesigner} onOpenUpload={() => setUploadOpen(true)} />

      <GlobalImageSearch
        input={globalSearchInput}
        systems={systems}
        selectedSystemCode={selectedSystemCode}
        onInputChange={setGlobalSearchInput}
        onSystemChange={selectSystem}
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
            onClear={clearGlobalSearch}
            onKeywordClick={executeGlobalSearch}
          />
        ) : (
          <div className="mt-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-medium">「{globalSearchKeyword}」的搜索结果</h2>
              <Button variant="ghost" size="sm" onClick={clearGlobalSearch}>清除搜索</Button>
            </div>
            <ImageGrid images={globalSearchImages} emptyText="未找到匹配的图片" />
          </div>
        )
      ) : (
        <>
          {isDesigner && (
            <LocalImageToolbar
              searchInput={searchInput}
              sortBy={sortBy}
              onSearchInputChange={setSearchInput}
              onKeywordChange={setKeyword}
              onSortByChange={setSortBy}
            />
          )}
          <section className="mt-6">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="size-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                <ImageGrid
                  images={images}
                  emptyText={keyword ? '未找到匹配的图片' : '图片库为空，可从上传主图开始'}
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
