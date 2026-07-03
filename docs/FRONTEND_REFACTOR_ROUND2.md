# 第二轮改造施工文档：前端状态与页面收口

版本：2026-07-02
适用范围：`client/` 前端
文档类型：改造施工手册（供人工按步骤执行）
前置状态：第一轮后端重构（拆分 `SearchAnalyticsService`、查询下沉 Repository）已完成，后端测试 90 passed、Ruff 通过、Pyright 全绿。

本文档遵循 `docs/OPTIMIZATION_PLAN.md` 的改造纪律：**只做前端，不动后端；一次只拆一个方向；每步都能单独验证；完成后补变更记录。**

---

## 0. 本轮目标与非目标

### 0.1 目标

把前端两个已经开始变重、且未来一定会继续膨胀的地方收口：

1. **`useImageBrowser.ts`（258 行，返回 40+ 字段）** —— 把"浏览分页 / 本地筛选 / 全局语义搜索 / 弹窗开关"四类互相纠缠的状态拆成独立 hook。
2. **`SemanticSearchResult.tsx`（360 行）** —— 内部已有子组件，但都挤在一个文件里，拆成独立文件目录。

### 0.2 非目标（本轮明确不做）

- 不动后端任何代码、API、响应结构。
- 不改任何接口的请求/返回字段。
- 不改 UI 视觉、交互行为、文案。**这是纯结构重构，用户应该看不出任何变化。**
- 不拆 `ImageDetail`（它只有 94 行，已经拆得很好，重的是 `ImageDetailInfoPanel`/`ImageAiAnalysisPanel`，留到后续轮次）。
- 不引入新依赖、不改路由。

---

## 1. 现状诊断（施工前必读）

### 1.1 `useImageBrowser.ts` 承担的四类职责

读一遍 `client/src/features/images/useImageBrowser.ts`，它的 state 可以清晰归为四组：

| 分组 | 涉及的 state / 逻辑 | 说明 |
|------|--------------------|------|
| **A. 浏览与分页** | `imageQuery`(useInfiniteQuery)、`images`、`sentinelRef`、无限滚动 `useEffect`、`hasMore`、`loading`、`loadingMore` | 标签目录下的图片列表 |
| **B. 本地筛选/排序** | `keyword`、`searchInput`、`filterTagIds`、`filterKeyword`、`filterCategory`、`sortBy`、`handleFilter`、`clearFilter`、`hasActiveFilter`、`filterLabel`、`effectiveTagIds` | 设计师工具栏 + 筛选弹窗 |
| **C. 全局语义搜索** | `globalSearchInput`、`globalSearchKeyword`、`globalSearchMode`、`semanticSearch`(useMutation)、`globalSearchTags`、`executeGlobalSearch`、`clearGlobalSearch`、`handleTagSuggestClick` | 首页顶部搜索框 |
| **D. 弹窗与派生 UI** | `uploadOpen`、`tagPanelOpen`、`filterDialogOpen`、`handleUploadSuccess`、`breadcrumb`、`currentTag`、`childTags`、`pageTitle`、`showChildTags`、`showImages`、`isRoot` | 弹窗开关 + 面包屑 + 展示条件 |

**耦合点**（拆分时要小心的地方）：
- `effectiveTagIds`（B）依赖 `parentTagId` + `keyword` + `filterKeyword`。
- `handleFilter`（B）会调用 `resetSemanticSearch` 并清空全局搜索 state（C）—— **筛选和全局搜索互斥**。
- `handleTagSuggestClick`（C）会调用 `handleFilter`（B）。
- `clearFilter`（B）清空 `keyword`/`searchInput`。
- `showImages` / `showChildTags`（D）依赖 `hasActiveFilter`（B）和 `parentTagId`。
- `ImageHome.tsx` 用 `shouldRenderImageSection = showImages && !globalSearchKeyword` 把 B/C/D 串起来。

> 这些跨组引用是本轮拆分的**主要风险**，务必保留原有联动语义。

### 1.2 `SemanticSearchResult.tsx` 现状

已经在同一文件内定义了子组件：`SearchUnderstandingPanel`、`ScoredImageCard`、`SearchResultGrid`、`SearchFeedbackPanel`，以及常量表 `RELATION_LABELS` / `MATCH_LEVEL_CONFIG` 等。问题只是**都堆在一个 360 行文件里**，不是逻辑纠缠。拆分难度低、风险低。

---

## 2. 目标结构

```text
client/src/features/images/
  useImageBrowser.ts          # 保留为「组合入口」，聚合下面几个 hook
  hooks/
    useImageListQuery.ts      # A. 浏览与分页（含无限滚动）
    useImageFilters.ts        # B. 本地筛选与排序
    useGlobalImageSearch.ts   # C. 全局语义搜索
    useImageBrowserUi.ts      # D. 弹窗开关 + 派生 UI（面包屑/展示条件）

client/src/pages/ImageHome/SemanticSearchResult/
  index.tsx                   # 主组件（原 SemanticSearchResult 的壳）
  SearchUnderstandingPanel.tsx
  ScoredImageCard.tsx
  SearchResultGrid.tsx
  SearchFeedbackPanel.tsx
  constants.ts                # RELATION_*/CAT_RELATION_*/MATCH_LEVEL_CONFIG/FEEDBACK_OPTIONS/动画 variants
```

> 关键约束：`useImageBrowser` 对外返回的字段名和 `ImageHome.tsx` 的用法**保持完全不变**，这样 `ImageHome.tsx` 几乎不用改（只有 import 路径可能微调）。这是"外部接口稳定"原则。

---

## 3. 施工步骤

> 建议顺序：先做风险最低的 `SemanticSearchResult`（第 3.1 步），验证一次；再做 `useImageBrowser`（第 3.2 步），验证一次。**不要两个一起改。**

### 3.1 步骤一：拆 `SemanticSearchResult`（低风险，先做）

这是纯文件搬运，逻辑零改动。

1. 新建目录 `client/src/pages/ImageHome/SemanticSearchResult/`。
2. 新建 `constants.ts`，把这些从原文件移入并 `export`：
   - `RELATION_LABELS`、`RELATION_COLORS`
   - `CAT_RELATION_LABELS`、`CAT_RELATION_COLORS`
   - `MATCH_LEVEL_CONFIG`
   - `staggerVariants`、`itemVariants`
   - `FEEDBACK_OPTIONS`
3. 新建 `SearchUnderstandingPanel.tsx` / `ScoredImageCard.tsx` / `SearchResultGrid.tsx` / `SearchFeedbackPanel.tsx`，每个搬一个子组件，从 `constants.ts` 引入所需常量。
   - 注意 `ScoredImageCard` 和 `SearchResultGrid` 都依赖 `itemVariants`/`staggerVariants`，从 `constants.ts` 引。
   - `SearchResultGrid` 依赖 `ScoredImageCard`。
4. 新建 `index.tsx`：保留主组件 `SemanticSearchResult`（含 `feedbackMutation`、`groupedResults`、整体布局），从上面几个文件引入子组件。
5. 删除原 `client/src/pages/ImageHome/SemanticSearchResult.tsx`。
6. `ImageHome.tsx` 里的 `import SemanticSearchResult from './SemanticSearchResult'` **无需改动**（目录含 `index.tsx` 时解析一致）。确认打包器（Vite）能解析目录 index；若报错，改成 `'./SemanticSearchResult/index'`。

**验证**：`cd client && npm run typecheck && npm run lint && npm run test && npm run build`，再本地打开首页搜索一次，确认理解面板、S/A/B/C 分组、反馈按钮都正常。

### 3.2 步骤二：拆 `useImageBrowser`（中等风险）

目标是把 258 行拆成 4 个子 hook + 1 个组合入口，**返回给 `ImageHome.tsx` 的对象结构一模一样**。

#### 3.2.1 新建 `hooks/useImageListQuery.ts`（A 组）

- 入参：`{ parentTagId?: string; keyword: string; filterKeyword: string; effectiveTagIds: string[] | undefined; sortBy; filterCategory }`
  - 说明：`effectiveTagIds` 由筛选 hook 计算后传入（见下），避免这个 hook 反向依赖筛选 state。
- 内部：`useInfiniteQuery`（原 62–82 行）、`images` memo、无限滚动 `useEffect`、`sentinelRef`。
- 返回：`{ images, sentinelRef, loading, loadingMore, hasMore }`。

#### 3.2.2 新建 `hooks/useImageFilters.ts`（B 组）

- 入参：`{ parentTagId?: string; allTags; onFilterApplied?: () => void }`
  - `onFilterApplied` 用来在筛选生效时通知全局搜索 hook 清空自己（替代原来 `handleFilter` 里直接调 `resetSemanticSearch`），保持 B 不直接依赖 C。
- 内部 state：`keyword`、`searchInput`、`filterTagIds`、`filterKeyword`、`filterCategory`、`sortBy`。
- 计算：`effectiveTagIds`、`hasActiveFilter`、`filterLabel`。
- 方法：`handleFilter`（末尾调用 `onFilterApplied?.()`）、`clearFilter`、`setKeyword`、`setSearchInput`、`setFilterCategory`、`setSortBy`。
- 返回上述 state + 计算值 + 方法。

#### 3.2.3 新建 `hooks/useGlobalImageSearch.ts`（C 组）

- 入参：`{ allTags; onBeforeFilterByTag: (tag) => void }` 或直接把 `handleFilter` 传进来（见联动说明）。
- 内部：`globalSearchInput`、`globalSearchKeyword`、`globalSearchMode`、`useDeferredValue`、`semanticSearch`(useMutation)、`globalSearchTags`。
- 方法：`executeGlobalSearch`、`clearGlobalSearch`、`handleTagSuggestClick`、`setGlobalSearchInput`、`setGlobalSearchMode`。
- 返回：`{ globalSearchImages, globalSearchInput, globalSearchKeyword, globalSearchLoading, globalSearchMode, globalSearchTags, semanticResult, executeGlobalSearch, clearGlobalSearch, handleTagSuggestClick, setGlobalSearchInput, setGlobalSearchMode }`。

#### 3.2.4 新建 `hooks/useImageBrowserUi.ts`（D 组）

- 入参：`{ parentTagId?: string; allTags; isDesigner; hasActiveFilter }`。
- 内部：`uploadOpen`、`tagPanelOpen`、`filterDialogOpen`、`handleUploadSuccess`（用 `useQueryClient`）。
- 计算：`currentTag`、`childTags`、`breadcrumb`、`isRoot`、`pageTitle`、`showChildTags`、`showImages`。
- 返回上述内容。

#### 3.2.5 改写 `useImageBrowser.ts` 为组合入口

- 调 `useTags()` 拿 `allTags`。
- 按依赖顺序组合：
  1. `filters = useImageFilters({ parentTagId, allTags, onFilterApplied: () => global.clearGlobalSearch() })`
  2. `global = useGlobalImageSearch({ allTags, handleFilter: filters.handleFilter })`
     - **循环依赖处理**：`filters` 需要 `global.clearGlobalSearch`，`global` 需要 `filters.handleFilter`。解决方式：用 `useRef` 持有回调，或把"筛选后清空全局搜索"的联动上提到组合入口里用 `useEffect`/包装函数完成，而不是让两个 hook 互相直接引用。**推荐**：在组合入口里包装 `handleFilter`：先 `filters.handleFilter(...)` 再 `global.clearGlobalSearch()`，把包装后的函数传给 `ImageHome`；`handleTagSuggestClick` 同理在入口层组合。
  3. `ui = useImageBrowserUi({ parentTagId, allTags, isDesigner, hasActiveFilter: filters.hasActiveFilter })`
  4. `list = useImageListQuery({ parentTagId, keyword: filters.keyword, filterKeyword: filters.filterKeyword, effectiveTagIds: filters.effectiveTagIds, sortBy: filters.sortBy, filterCategory: filters.filterCategory })`
- **返回一个和现在字段完全一致的对象**（对照当前 `useImageBrowser` 210–257 行逐字段核对）。

> 核对清单：把当前 return 的 40+ 个字段列出来，逐个确认在新结构里有对应来源。字段名一个都不能改，否则 `ImageHome.tsx` 会 typecheck 报错（这其实是好事，能帮你抓到遗漏）。

**验证**：`cd client && npm run typecheck && npm run lint && npm run test && npm run build`，然后本地手动回归：
- 根目录：全局搜索（精准/智能切换）、标签建议点击、清除搜索。
- 进入某个标签：子标签展示、图片列表、无限滚动、排序、分类筛选。
- 打开筛选弹窗筛选后，确认全局搜索被清空（互斥联动没坏）。
- 上传弹窗、标签面板打开关闭、上传成功后列表刷新。

---

## 4. 验收标准（对齐 OPTIMIZATION_PLAN.md 第 0.5 节）

- `npm run typecheck` 通过。
- `npm run lint` 通过。
- `npm run test`（vitest）通过。
- `npm run build` 成功。
- 首页浏览、标签下钻、无限滚动、本地筛选、全局语义搜索、搜索反馈、上传、标签面板**行为与改造前完全一致**。
- 后端**未改动**（本轮不碰后端，CI backend job 应与改造前一致）。

---

## 5. 完成后必须补的变更记录

改完在 `docs/OPTIMIZATION_PLAN.md` 第 12 节"改造变更记录"末尾追加一条，格式：

```md
### YYYY-MM-DD：第二轮前端优化 - useImageBrowser 与搜索结果组件收口

改造目标：
- 拆分 useImageBrowser 的浏览/筛选/全局搜索/UI 四类职责。
- 拆分 SemanticSearchResult 为独立组件目录。

实际改动：
- 新增 hooks/useImageListQuery、useImageFilters、useGlobalImageSearch、useImageBrowserUi。
- useImageBrowser 收口为组合入口，对外返回字段不变。
- SemanticSearchResult 拆为 index + 子组件 + constants。

明确没有改动：
- 没有改动后端、API、响应字段。
- 没有改动 UI 视觉、交互和文案。
- 没有引入新依赖或改路由。

验证结果：
- 前端 typecheck / lint / test / build：
- 手工回归（搜索/筛选/浏览/上传）：

风险与遗留：
- ImageDetailInfoPanel / ImageAiAnalysisPanel 仍偏重，留到后续轮次。

下一步：
- 视需要再拆详情页信息面板。
```

---

## 6. 回滚策略

本轮全部改动在 `client/` 内、且是结构性拆分。若任一验证失败且短时间定位不到：
- `git checkout -- client/`（未提交时）或 `git revert`（已提交时）即可整轮回滚，不影响后端第一轮成果。
- 建议**步骤一提交一次、步骤二提交一次**，两个独立 commit，方便单独回滚。
