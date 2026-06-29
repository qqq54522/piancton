import { useState } from 'react';
import { X, Sparkles, Target, Layers, Search, AlertTriangle, MessageSquare } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { Button } from '@client/src/components/ui/button';
import { Badge } from '@client/src/components/ui/badge';
import { Input } from '@client/src/components/ui/input';
import { motion } from 'framer-motion';
import { submitSearchFeedback } from '@client/src/api/image';
import type {
  SearchFeedbackType,
  SearchMode,
  SemanticSearchResponse,
  ScoredImageMatch,
  SearchUnderstanding,
} from '@client/src/types/api';
import ImageCard from './ImageCard';

interface SemanticSearchResultProps {
  keyword: string;
  result: SemanticSearchResponse;
  searchMode: SearchMode;
  onClear: () => void;
  onKeywordClick: (kw: string) => void;
}

const RELATION_LABELS: Record<string, string> = {
  exact: '精准',
  strong: '强相关',
  medium: '中相关',
  weak: '弱相关',
};

const RELATION_COLORS: Record<string, string> = {
  exact: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  strong: 'bg-blue-100 text-blue-800 border-blue-200',
  medium: 'bg-amber-100 text-amber-800 border-amber-200',
  weak: 'bg-gray-100 text-gray-600 border-gray-200',
};

const CAT_RELATION_LABELS: Record<string, string> = {
  direct: '直接',
  related: '相关',
  fallback: '兜底',
};

const CAT_RELATION_COLORS: Record<string, string> = {
  direct: 'bg-purple-100 text-purple-800 border-purple-200',
  related: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  fallback: 'bg-gray-100 text-gray-600 border-gray-200',
};

const MATCH_LEVEL_CONFIG: Record<string, { label: string; color: string; icon: typeof Target }> = {
  S: { label: '精准推荐', color: 'bg-emerald-500 text-white', icon: Target },
  A: { label: '高度相似', color: 'bg-blue-500 text-white', icon: Layers },
  B: { label: '同类相关', color: 'bg-amber-500 text-white', icon: Search },
  C: { label: '兜底推荐', color: 'bg-gray-400 text-white', icon: Search },
};

const staggerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
};

function SearchUnderstandingPanel({ understanding, onKeywordClick }: { understanding: SearchUnderstanding; onKeywordClick: (kw: string) => void }) {
  return (
    <div className="mb-5 space-y-3">
      {understanding.searchIntent && (
        <div className="flex items-start gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3.5 py-2.5">
          <Sparkles className="mt-0.5 size-4 flex-shrink-0 text-primary" />
          <div>
            <p className="text-sm leading-relaxed text-primary/90">{understanding.searchIntent}</p>
            {understanding.queryType && (
              <Badge variant="outline" className="mt-1.5 text-xs text-primary/70">
                {understanding.queryType}
              </Badge>
            )}
          </div>
        </div>
      )}

      {understanding.normalizedQuery !== understanding.originalQuery && (
        <p className="text-xs text-muted-foreground">
          标准化：{understanding.originalQuery} → {understanding.normalizedQuery}
        </p>
      )}

      {understanding.expandedLevel1Tags.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-foreground/70">扩展标签</span>
          {(['exact', 'strong', 'medium', 'weak'] as const).map((relation) => {
            const tagsOfRelation = understanding.expandedLevel1Tags.filter((t) => t.relation === relation);
            if (tagsOfRelation.length === 0) return null;
            return (
              <div key={relation} className="flex flex-wrap items-center gap-1.5">
                <Badge
                  variant="outline"
                  className={`flex-shrink-0 border text-xs font-medium ${RELATION_COLORS[relation]}`}
                >
                  {RELATION_LABELS[relation]}
                </Badge>
                {tagsOfRelation.map((et) => (
                  <button
                    key={et.tag}
                    onClick={() => onKeywordClick(et.tag)}
                    className="rounded-md border border-border bg-background px-2 py-0.5 text-xs text-foreground transition-colors hover:bg-accent"
                    title={et.reason}
                  >
                    {et.tag}
                    <span className="ml-1 text-[10px] text-muted-foreground">{Math.round(et.weight * 100)}</span>
                  </button>
                ))}
              </div>
            );
          })}
        </div>
      )}

      {understanding.matchedLevel2Categories.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-foreground/70">匹配大类</span>
          {(['direct', 'related', 'fallback'] as const).map((relation) => {
            const catsOfRelation = understanding.matchedLevel2Categories.filter((c) => c.relation === relation);
            if (catsOfRelation.length === 0) return null;
            return (
              <div key={relation} className="flex flex-wrap items-center gap-1.5">
                <Badge
                  variant="outline"
                  className={`flex-shrink-0 border text-xs font-medium ${CAT_RELATION_COLORS[relation]}`}
                >
                  {CAT_RELATION_LABELS[relation]}
                </Badge>
                {catsOfRelation.map((mc) => (
                  <span
                    key={mc.category}
                    className="rounded-md bg-purple-50 px-2 py-0.5 text-xs text-purple-700"
                    title={mc.reason}
                  >
                    {mc.category}
                  </span>
                ))}
              </div>
            );
          })}
        </div>
      )}

      {understanding.excludeTags.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-medium text-red-500">排除</span>
          {understanding.excludeTags.map((tag) => (
            <span key={tag} className="rounded-md bg-red-50 px-2 py-0.5 text-xs text-red-400 line-through">
              {tag}
            </span>
          ))}
        </div>
      )}

      {understanding.searchStrategy && (
        <p className="text-xs text-muted-foreground/80 italic">{understanding.searchStrategy}</p>
      )}
    </div>
  );
}

function ScoredImageCard({ scored }: { scored: ScoredImageMatch }) {
  const config = MATCH_LEVEL_CONFIG[scored.matchLevel];
  const LevelIcon = config.icon;

  const overlay = (
    <>
      <div className="absolute left-2 top-2 flex items-center gap-1">
        <Badge className={`${config.color} text-[10px] font-medium shadow-sm`}>
          <LevelIcon className="mr-0.5 size-3" />
          {scored.matchLevel} {config.label}
        </Badge>
      </div>
      {scored.matchReasons.length > 0 && (
        <div className="absolute bottom-2 left-2 right-2">
          <div className="rounded bg-background/90 px-1.5 py-0.5 text-[10px] leading-tight text-foreground/80 shadow-sm backdrop-blur-sm line-clamp-1">
            {scored.matchReasons[0]}
          </div>
        </div>
      )}
    </>
  );

  return (
    <motion.div variants={itemVariants} className="space-y-2">
      <ImageCard image={scored.image} overlay={overlay} />
      {scored.matchReasons.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {scored.matchReasons.slice(0, 3).map((reason) => (
            <Badge key={reason} variant="outline" className="max-w-full truncate text-[10px] font-normal">
              {reason}
            </Badge>
          ))}
        </div>
      )}
    </motion.div>
  );
}

const FEEDBACK_OPTIONS: Array<{ type: SearchFeedbackType; label: string }> = [
  { type: 'not_relevant', label: '结果不相关' },
  { type: 'too_few_results', label: '结果太少' },
  { type: 'need_different_style', label: '想要别的风格' },
  { type: 'asset_request', label: '提交素材需求' },
];

const SemanticSearchResult = ({ keyword, result, searchMode, onClear, onKeywordClick }: SemanticSearchResultProps) => {
  const understanding = result.searchUnderstanding;
  const hasResults = result.results.length > 0;
  const [feedbackNote, setFeedbackNote] = useState('');
  const [submittedFeedback, setSubmittedFeedback] = useState<SearchFeedbackType | null>(null);
  const feedbackMutation = useMutation({
    mutationFn: (feedbackType: SearchFeedbackType) => submitSearchFeedback({
      searchLogId: result.searchLogId,
      keyword,
      feedbackType,
      note: feedbackNote.trim() || undefined,
    }),
    onSuccess: (_data, feedbackType) => {
      setSubmittedFeedback(feedbackType);
      setFeedbackNote('');
    },
  });

  const groupedResults = {
    S: result.results.filter((r) => r.matchLevel === 'S'),
    A: result.results.filter((r) => r.matchLevel === 'A'),
    B: result.results.filter((r) => r.matchLevel === 'B'),
    C: result.results.filter((r) => r.matchLevel === 'C'),
  };

  return (
    <div className="mt-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-medium text-foreground">
          「{keyword}」的搜索结果
          <Badge className="ml-2 bg-muted text-muted-foreground border-border text-xs">
            {searchMode === 'smart' ? '智能搜索' : '精准搜索'}
          </Badge>
          {result.searchMode === 'meilisearch' && (
            <Badge className="ml-2 bg-blue-50 text-blue-700 border-blue-200 text-xs">
              Meilisearch
            </Badge>
          )}
        </h2>
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X className="mr-1 size-3.5" />
          清除搜索
        </Button>
      </div>

      {result.fallback && (
        <div className="mb-4 flex items-center gap-1.5 rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5">
          <AlertTriangle className="size-3.5 text-amber-600" />
          <span className="text-xs text-amber-700">
            智能搜索已降级为精准搜索{result.fallbackReason ? `（${result.fallbackReason}）` : ''}
          </span>
        </div>
      )}

      {understanding && (
        <SearchUnderstandingPanel understanding={understanding} onKeywordClick={onKeywordClick} />
      )}

      {result.matchSummary && (
        <p className="mb-3 text-sm text-muted-foreground">{result.matchSummary}</p>
      )}

      {!hasResults ? (
        <div className="flex flex-col items-center justify-center py-20">
          <p className="text-sm text-muted-foreground">未找到相关图片</p>
        </div>
      ) : (
        <div className="space-y-6">
          {(['S', 'A', 'B', 'C'] as const).map((level) => {
            const items = groupedResults[level];
            if (items.length === 0) return null;
            const config = MATCH_LEVEL_CONFIG[level];
            return (
              <div key={level}>
                <div className="mb-2 flex items-center gap-2">
                  <Badge className={`${config.color} text-xs`}>
                    {level}级 · {config.label}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{items.length} 张</span>
                </div>
                <motion.div
                  className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4"
                  initial="hidden"
                  animate="visible"
                  variants={staggerVariants}
                >
                  {items.map((scored) => (
                    <ScoredImageCard key={scored.image.id} scored={scored} />
                  ))}
                </motion.div>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-6 border-t border-border pt-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MessageSquare className="size-4" />
            <span>这次搜索结果是否满足需求？</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {FEEDBACK_OPTIONS.map((option) => (
              <Button
                key={option.type}
                variant={submittedFeedback === option.type ? 'default' : 'outline'}
                size="sm"
                disabled={feedbackMutation.isPending}
                onClick={() => feedbackMutation.mutate(option.type)}
              >
                {option.label}
              </Button>
            ))}
          </div>
        </div>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <Input
            value={feedbackNote}
            onChange={(event) => setFeedbackNote(event.target.value)}
            placeholder="可选：补充你想找的画面、风格或业务话术"
            className="h-9 text-sm"
            maxLength={200}
          />
          <Button
            variant="ghost"
            size="sm"
            disabled={!feedbackNote.trim() || feedbackMutation.isPending}
            onClick={() => feedbackMutation.mutate('asset_request')}
          >
            提交说明
          </Button>
        </div>
        {submittedFeedback && (
          <p className="mt-2 text-xs text-emerald-600">已记录反馈，管理员会在搜索运营里看到。</p>
        )}
      </div>
    </div>
  );
};

export default SemanticSearchResult;
