import { Sparkles } from 'lucide-react';
import { Badge } from '@client/src/components/ui/badge';
import type { SearchUnderstanding } from '@client/src/types/api';
import {
  CAT_RELATION_COLORS,
  CAT_RELATION_LABELS,
  RELATION_COLORS,
  RELATION_LABELS,
} from './constants';

interface SearchUnderstandingPanelProps {
  understanding: SearchUnderstanding;
  onKeywordClick: (kw: string) => void;
}

function SearchUnderstandingPanel({ understanding, onKeywordClick }: SearchUnderstandingPanelProps) {
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

export default SearchUnderstandingPanel;
