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
  strong: 'bg-blue-100 text-blue-800 border-blue-200',
  medium: 'bg-amber-100 text-amber-800 border-amber-200',
  weak: 'bg-gray-100 text-gray-600 border-gray-200',
};

export const CAT_RELATION_LABELS: Record<string, string> = {
  direct: '直接',
  related: '相关',
  fallback: '兜底',
};

export const CAT_RELATION_COLORS: Record<string, string> = {
  direct: 'bg-purple-100 text-purple-800 border-purple-200',
  related: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  fallback: 'bg-gray-100 text-gray-600 border-gray-200',
};

export const MATCH_LEVEL_CONFIG: Record<string, { label: string; color: string; icon: typeof Target }> = {
  S: { label: '精准推荐', color: 'bg-emerald-500 text-white', icon: Target },
  A: { label: '高度相似', color: 'bg-blue-500 text-white', icon: Layers },
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
  { type: 'too_few_results', label: '结果太少' },
  { type: 'need_different_style', label: '想要别的风格' },
  { type: 'asset_request', label: '提交素材需求' },
];
