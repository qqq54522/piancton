import { Link } from 'react-router-dom';
import {
  Search, Upload, Tags, X, ImageOff, Loader2,
  FolderOpen, Home, ChevronRight, SlidersHorizontal, ArrowUpDown, FileClock, Sparkles,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { CanRole, useAuth, ROLE_SUBJECT } from '@client/src/lib/auth';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@client/src/components/ui/dropdown-menu';
import ImageCard from './ImageCard';
import TagCard from './TagCard';
import UploadDialog from './UploadDialog';
import TagPanel from './TagPanel';
import FilterDialog from './FilterDialog';
import SemanticSearchResult from './SemanticSearchResult';
import { useImageBrowser } from '@client/src/features/images/useImageBrowser';

interface ImageBrowserProps {
  parentTagId?: string;
}

const staggerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

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

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          {pageTitle}
        </h1>
        <div className="flex items-center gap-2">
          {isRoot && !isDesigner && (
            <Button variant="outline" size="sm" onClick={() => setFilterDialogOpen(true)}>
              <SlidersHorizontal className="mr-1.5 size-4" />
              精确查找
            </Button>
          )}
          <CanRole roles={['designer']}>
            {isRoot && (
              <Button variant="outline" size="sm" asChild>
                <Link to="/trash">
                  <FileClock className="mr-1.5 size-4" />
                  回收站
                </Link>
              </Button>
            )}
          </CanRole>
          <CanRole roles={['designer']}>
            {isRoot && (
              <Button variant="outline" size="sm" onClick={() => setTagPanelOpen(true)}>
                <Tags className="mr-1.5 size-4" />
                标签管理
              </Button>
            )}
          </CanRole>
          <CanRole roles={['designer']}>
            {isRoot && (
              <Button size="sm" onClick={() => setUploadOpen(true)}>
                <Upload className="mr-1.5 size-4" />
                上传图片
              </Button>
            )}
          </CanRole>
        </div>
      </div>

      {isRoot && (
        <div className="relative mt-5">
          <div className="relative mx-auto max-w-2xl">
            <Search className="absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground/60" />
            <Input
              placeholder="搜索标签或图片..."
              value={globalSearchInput}
              onChange={(e) => setGlobalSearchInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') executeGlobalSearch(); }}
              className="h-12 rounded-xl pl-11 pr-20 text-base md:text-base shadow-sm"
            />
            {globalSearchInput && (
              <button
                onClick={clearGlobalSearch}
                className="absolute right-20 top-1/2 z-10 flex h-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            )}
            <button
              onClick={() => executeGlobalSearch()}
              className="absolute right-2 top-1/2 z-10 flex h-8 -translate-y-1/2 items-center rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 whitespace-nowrap"
            >
              搜索
            </button>
          </div>
          <div className="mx-auto mt-2 flex max-w-2xl items-center justify-center gap-2 text-xs">
            <button
              type="button"
              onClick={() => setGlobalSearchMode('precise')}
              className={`rounded-full border px-3 py-1 transition-colors ${globalSearchMode === 'precise' ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background text-muted-foreground hover:text-foreground'}`}
              title="适合搜索完整标题、明确标签、六大体系或二级分类"
            >
              精准搜索
            </button>
            <button
              type="button"
              onClick={() => setGlobalSearchMode('smart')}
              className={`inline-flex items-center rounded-full border px-3 py-1 transition-colors ${globalSearchMode === 'smart' ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background text-muted-foreground hover:text-foreground'}`}
              title="适合搜索一句模糊需求、家长痛点或业务表达；不可用时会自动兜底"
            >
              <Sparkles className="mr-1 size-3" />
              智能搜索
            </button>
          </div>
          {globalSearchInput.trim() && globalSearchTags.length > 0 && !globalSearchKeyword && (
            <div className="absolute left-0 right-0 z-50 mx-auto mt-1 max-w-2xl overflow-hidden rounded-xl border border-border bg-popover p-2 shadow-lg">
              <p className="mb-1.5 px-2 text-xs font-medium text-muted-foreground">匹配标签</p>
              {globalSearchTags.map((tag) => (
                <button
                  key={tag.id}
                  onClick={() => handleTagSuggestClick(tag)}
                  className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-accent"
                >
                  <span
                    className="size-2.5 flex-shrink-0 rounded-full"
                    style={{ backgroundColor: tag.color || '#6B7280' }}
                  />
                  <span className="flex-1 text-sm text-foreground">{tag.name}</span>
                  <span className="text-xs text-muted-foreground">{tag.imageCount ?? 0} 张</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {breadcrumb.length > 1 && (
        <nav className="mt-4 flex flex-wrap items-center gap-1 text-sm">
          {breadcrumb.map((item, idx) => (
            <span key={item.id ?? 'root'} className="flex items-center gap-1">
              {idx > 0 && (
                <ChevronRight className="size-3.5 text-muted-foreground/50" />
              )}
              {idx === breadcrumb.length - 1 ? (
                <span className="font-medium text-foreground">{item.name}</span>
              ) : (
                <Link
                  to={item.id ? `/tag/${item.id}` : '/'}
                  className="flex items-center gap-1 text-muted-foreground hover:text-foreground"
                >
                  {idx === 0 && <Home className="size-3.5" />}
                  {item.name}
                </Link>
              )}
            </span>
          ))}
        </nav>
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
              {globalSearchImages.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20">
                  <ImageOff className="size-12 text-muted-foreground/50" />
                  <p className="mt-3 text-sm text-muted-foreground">未找到匹配的图片</p>
                </div>
              ) : (
                <motion.div
                  className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4"
                  initial="hidden"
                  animate="visible"
                  variants={staggerVariants}
                >
                  {globalSearchImages.map((image) => (
                    <motion.div key={image.id} variants={itemVariants}>
                      <ImageCard image={image} />
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </div>
          )}
        </>
      )}

      {showImages && (
        <>
          <CanRole roles={['designer']}>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="搜索标题、标签、业务表达..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') setKeyword(searchInput); }}
                  className="pl-9"
                />
                {searchInput && (
                  <button
                    onClick={() => { setSearchInput(''); setKeyword(''); }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="size-4" />
                  </button>
                )}
              </div>
              <Button variant="outline" size="sm" onClick={() => setKeyword(searchInput)}>
                搜索
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <ArrowUpDown className="mr-1.5 size-4" />
                    {filterCategory === 'scene' ? '筛选场景' : filterCategory === 'function' ? '筛选功能' : sortBy === 'downloadCount' ? '下载量' : '最新上传'}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => { setSortBy('createdAt'); setFilterCategory(undefined); }}>
                    最新上传
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => { setSortBy('downloadCount'); setFilterCategory(undefined); }}>
                    下载量最多
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => setFilterCategory(filterCategory === 'scene' ? undefined : 'scene')}
                    className={filterCategory === 'scene' ? 'bg-primary/10 font-medium text-primary' : ''}
                  >
                    筛选场景
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => setFilterCategory(filterCategory === 'function' ? undefined : 'function')}
                    className={filterCategory === 'function' ? 'bg-primary/10 font-medium text-primary' : ''}
                  >
                    筛选功能
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
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
            ) : images.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20">
                <ImageOff className="size-12 text-muted-foreground/50" />
                <p className="mt-3 text-sm text-muted-foreground">
                  {keyword ? '未找到匹配的图片' : '该标签下暂无图片'}
                </p>
              </div>
            ) : (
              <>
                <motion.div
                  className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4"
                  initial="hidden"
                  animate="visible"
                  variants={staggerVariants}
                >
                  <AnimatePresence>
                    {images.map((image) => (
                      <motion.div
                        key={image.id}
                        variants={itemVariants}
                        layout
                      >
                        <ImageCard image={image} />
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </motion.div>

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
