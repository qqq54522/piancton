import { FolderOpen, Loader2, SlidersHorizontal, Tags, X } from 'lucide-react';
import { motion } from 'framer-motion';
import { CanRole, useAuth, ROLE_SUBJECT } from '@client/src/lib/auth';
import { Button } from '@client/src/components/ui/button';
import TagCard from './TagCard';
import UploadDialog from './UploadDialog';
import TagPanel from './TagPanel';
import FilterDialog from './FilterDialog';
import SemanticSearchResult from './SemanticSearchResult';
import { useImageBrowser } from '@client/src/features/images/useImageBrowser';
import GlobalImageSearch from './GlobalImageSearch';
import ImageBreadcrumb from './ImageBreadcrumb';
import ImageGrid, { itemVariants, staggerVariants } from './ImageGrid';
import ImageHomeHeader from './ImageHomeHeader';
import LocalImageToolbar from './LocalImageToolbar';

interface ImageBrowserProps {
  parentTagId?: string;
}

const ImageBrowser = ({ parentTagId }: ImageBrowserProps) => {
  const canDesign = useAuth();
  const isDesigner = !canDesign.isLoading && canDesign.ability.can('designer', ROLE_SUBJECT);
  const browser = useImageBrowser(parentTagId, isDesigner);
  const {
    allTags, breadcrumb, childTags, clearFilter, clearGlobalSearch,
    executeGlobalSearch, filterCategory, filterDialogOpen, filterLabel,
    globalSearchImages, globalSearchInput, globalSearchKeyword,
    globalSearchLoading, globalSearchMode, globalSearchTags, handleFilter, handleTagSuggestClick,
    handleUploadSuccess, hasActiveFilter, hasMore, images, isRoot, keyword, loading,
    loadingMore, pageTitle, searchInput, semanticResult, sentinelRef,
    setFilterCategory, setFilterDialogOpen, setGlobalSearchInput, setGlobalSearchMode, setKeyword,
    setSearchInput, setSortBy, setTagPanelOpen, setUploadOpen, showChildTags,
    showImages, sortBy, tagPanelOpen, uploadOpen,
  } = browser;
  const shouldRenderImageSection = showImages && !globalSearchKeyword;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <ImageHomeHeader
        pageTitle={pageTitle}
        isRoot={isRoot}
        isDesigner={isDesigner}
        onOpenFilter={() => setFilterDialogOpen(true)}
        onOpenTagPanel={() => setTagPanelOpen(true)}
        onOpenUpload={() => setUploadOpen(true)}
      />

      {isRoot && (
        <GlobalImageSearch
          input={globalSearchInput}
          keyword={globalSearchKeyword}
          mode={globalSearchMode}
          suggestedTags={globalSearchTags}
          onInputChange={setGlobalSearchInput}
          onModeChange={setGlobalSearchMode}
          onClear={clearGlobalSearch}
          onSearch={executeGlobalSearch}
          onTagSuggestClick={handleTagSuggestClick}
        />
      )}

      {breadcrumb.length > 1 && (
        <ImageBreadcrumb items={breadcrumb} />
      )}

      {isRoot && allTags.length === 0 && !loading && (
        <div className="flex flex-col items-center justify-center py-20">
          <FolderOpen className="size-12 text-muted-foreground/50" />
          <p className="mt-3 text-sm text-muted-foreground">
            暂无标签，请先创建标签分类
          </p>
          <CanRole roles={['designer']}>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => setTagPanelOpen(true)}
            >
              <Tags className="mr-1.5 size-4" />
              管理标签
            </Button>
          </CanRole>
        </div>
      )}

      {showChildTags && !globalSearchKeyword && (
        <section className="mt-6">
          {!isRoot && (
            <h2 className="mb-3 text-sm font-medium text-muted-foreground">子标签</h2>
          )}
          <motion.div
            className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4"
            initial="hidden"
            animate="visible"
            variants={staggerVariants}
          >
            {childTags.map((tag) => (
              <motion.div key={tag.id} variants={itemVariants}>
                <TagCard tag={tag} />
              </motion.div>
            ))}
          </motion.div>
        </section>
      )}

      {isRoot && hasActiveFilter && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
          <SlidersHorizontal className="size-4 text-amber-600" />
          <span className="text-sm text-amber-800">
            筛选条件：<span className="font-medium">{filterLabel}</span>
          </span>
          <Button variant="ghost" size="sm" className="ml-auto h-7 text-xs" onClick={clearFilter}>
            <X className="mr-1 size-3" />
            清除筛选
          </Button>
        </div>
      )}

      {isRoot && globalSearchKeyword && (
        <>
          {globalSearchLoading ? (
            <div className="mt-6 flex flex-col items-center justify-center py-20">
              <Loader2 className="size-6 animate-spin text-primary" />
              <p className="mt-3 text-sm text-muted-foreground">正在搜索匹配素材...</p>
            </div>
          ) : semanticResult ? (
            <SemanticSearchResult
              keyword={globalSearchKeyword}
              result={semanticResult}
              searchMode={globalSearchMode}
              onClear={clearGlobalSearch}
              onKeywordClick={executeGlobalSearch}
            />
          ) : (
            <div className="mt-6">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-medium text-foreground">
                  「{globalSearchKeyword}」的搜索结果
                </h2>
                <Button variant="ghost" size="sm" onClick={clearGlobalSearch}>
                  清除搜索
                </Button>
              </div>
              <ImageGrid images={globalSearchImages} emptyText="未找到匹配的图片" />
            </div>
          )}
        </>
      )}

      {shouldRenderImageSection && (
        <>
          <CanRole roles={['designer']}>
            <LocalImageToolbar
              searchInput={searchInput}
              filterCategory={filterCategory}
              sortBy={sortBy}
              onSearchInputChange={setSearchInput}
              onKeywordChange={setKeyword}
              onFilterCategoryChange={setFilterCategory}
              onSortByChange={setSortBy}
            />
          </CanRole>

          <section className="mt-6">
            {!isRoot && showChildTags && !hasActiveFilter && !globalSearchKeyword && (
              <h2 className="mb-3 text-sm font-medium text-muted-foreground">
                当前标签图片
              </h2>
            )}
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="size-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                <ImageGrid
                  images={images}
                  emptyText={keyword ? '未找到匹配的图片' : '该标签下暂无图片'}
                  withPresence
                />

                <div ref={sentinelRef} className="mt-4 flex justify-center py-4">
                  {loadingMore && (
                    <Loader2 className="size-5 animate-spin text-muted-foreground" />
                  )}
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
        tags={allTags}
        onSuccess={handleUploadSuccess}
      />
      <TagPanel
        open={tagPanelOpen}
        onOpenChange={setTagPanelOpen}
        tags={allTags}
        selectedTagIds={[]}
        onTagClick={() => setTagPanelOpen(false)}
        onTagsChanged={handleUploadSuccess}
      />
      <FilterDialog
        open={filterDialogOpen}
        onOpenChange={setFilterDialogOpen}
        tags={allTags}
        onFilter={handleFilter}
      />
    </div>
  );
};

export default ImageBrowser;
