import { Layers, Search, Target } from 'lucide-react';
import type { SearchFeedbackType } from '@client/src/types/api';

export const RELATION_LABELS: Record<string, string> = {
  exact: '精准',
  strong: '强相关',
  medium: '中相关',
  weak: '弱相关',
};

export const RELATION_COLORS: Record<string, string> = {
  exact: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  strong: 'bg-stone-100 text-stone-800 border-stone-200',
  medium: 'bg-amber-100 text-amber-800 border-amber-200',
  weak: 'bg-gray-100 text-gray-600 border-gray-200',
};

export const CAT_RELATION_LABELS: Record<string, string> = {
  direct: '直接',
  related: '相关',
  fallback: '兜底',
};

export const CAT_RELATION_COLORS: Record<string, string> = {
  direct: 'bg-stone-100 text-stone-800 border-stone-200',
  related: 'bg-zinc-100 text-zinc-800 border-zinc-200',
  fallback: 'bg-gray-100 text-gray-600 border-gray-200',
};

export const MATCH_LEVEL_CONFIG: Record<string, { label: string; color: string; icon: typeof Target }> = {
  S: { label: '精准推荐', color: 'bg-emerald-500 text-white', icon: Target },
  A: { label: '高度相似', color: 'bg-stone-900 text-white', icon: Layers },
  B: { label: '同类相关', color: 'bg-amber-500 text-white', icon: Search },
  C: { label: '兜底推荐', color: 'bg-gray-400 text-white', icon: Search },
};

export const staggerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
};

export const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
};

export const FEEDBACK_OPTIONS: Array<{ type: SearchFeedbackType; label: string }> = [
  { type: 'not_relevant', label: '结果不相关' },
  { type: 'right_business_wrong_visual', label: '卖点对画面不对' },
  { type: 'right_visual_wrong_business', label: '画面对卖点不对' },
  { type: 'wrong_version', label: '版本/尺寸不对' },
  { type: 'too_few_results', label: '结果太少' },
  { type: 'need_different_style', label: '想要别的渠道' },
  { type: 'asset_request', label: '没有合适素材提交需求' },
];
