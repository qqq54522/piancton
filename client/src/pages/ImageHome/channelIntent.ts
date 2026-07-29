import { CHANNEL_VALUES, channelRecommendationFor } from './channelRecommendations';

export type ChannelFamily = 'ppt' | 'brand_manual' | 'mobile' | 'website' | 'unknown';
export type ChannelSize = 'large' | 'small' | 'unspecified';
export type ScenePreference = 'scene' | 'non_scene' | 'unspecified';
export type IntentConfidence = 'high' | 'medium' | 'low';

export interface ImageChannelIntent {
  channelFamily: ChannelFamily;
  channelSize: ChannelSize;
  exactChannel: string | null;
  candidateChannels: string[];
  scenePreference: ScenePreference;
  confidence: IntentConfidence;
  evidence: string[];
  recommendation: string;
}

export interface ChannelIntentEntry {
  value: string;
  family: Exclude<ChannelFamily, 'unknown'>;
  size: ChannelSize;
  phrases: string[];
  recommendationDescription?: string;
}

export const DEFAULT_CHANNEL_INTENT_ENTRIES: ChannelIntentEntry[] = [
  {
    value: 'PPT',
    family: 'ppt',
    size: 'unspecified',
    phrases: ['PPT', '幻灯片', '演示', '汇报', '提案', '销售讲解', '路演', '宣讲'],
  },
  {
    value: '品牌手册',
    family: 'brand_manual',
    size: 'unspecified',
    phrases: ['品牌手册', '品牌规范', '视觉规范', '品牌书', 'brand book', '品牌资料', '对外手册'],
  },
  {
    value: '手机端大图',
    family: 'mobile',
    size: 'large',
    phrases: ['手机端大图', '移动端首屏', 'App 首屏', '小程序首屏', '手机 banner', '手机端主视觉', '手机宣传图', '手机活动页'],
  },
  {
    value: '手机端小图',
    family: 'mobile',
    size: 'small',
    phrases: ['手机端小图', '移动端入口', 'App 列表图', '小程序入口图', '手机缩略图', '手机小卡片', '小屏图', '信息流小图'],
  },
  {
    value: '官网大图',
    family: 'website',
    size: 'large',
    phrases: ['官网大图', '官网首屏', '网站首屏', '官网 banner', '官网 hero', '官网主视觉', '首页头图'],
  },
  {
    value: '官网小图',
    family: 'website',
    size: 'small',
    phrases: ['官网小图', '官网模块图', '网站列表图', '官网入口图', '网页卡片图', '功能区小图'],
  },
];

const CHANNEL_FAMILY_LABELS: Record<ChannelFamily, string> = {
  ppt: 'PPT',
  brand_manual: '品牌手册',
  mobile: '手机端',
  website: '官网',
  unknown: '',
};

const FAMILY_CANDIDATES: Record<Exclude<ChannelFamily, 'unknown'>, string[]> = {
  ppt: ['PPT'],
  brand_manual: ['品牌手册'],
  mobile: ['手机端大图', '手机端小图'],
  website: ['官网大图', '官网小图'],
};

const FAMILY_PATTERNS: Array<{ family: Exclude<ChannelFamily, 'unknown'>; patterns: RegExp[] }> = [
  {
    family: 'ppt',
    patterns: [/ppt/i, /幻灯片/, /演示/, /汇报/, /提案/, /销售讲解/, /路演/, /宣讲/],
  },
  {
    family: 'brand_manual',
    patterns: [/品牌手册/, /品牌规范/, /视觉规范/, /品牌书/, /brand\s*book/i, /品牌资料/, /对外手册/],
  },
  {
    family: 'mobile',
    patterns: [/手机端/, /移动端/, /\bapp\b/i, /小程序/, /\bh5\b/i, /手机里/, /手机上/, /移动页面/, /朋友圈/, /微信朋友圈/, /社媒/, /社交平台/],
  },
  {
    family: 'website',
    patterns: [/官网/, /网站/, /\bweb\b/i, /网页/, /落地页/, /首页/, /产品页/],
  },
];

const LARGE_PATTERNS = [
  /大图/,
  /首屏/,
  /\bbanner\b/i,
  /\bhero\b/i,
  /头图/,
  /主视觉/,
  /活动页/,
  /宣传图/,
  /海报/,
  /顶部/,
  /朋友圈(?!.*(?:九宫格|小图|小屏|列表|入口|缩略图|小卡片|信息流|推荐位|图标位|宫格))/,
  /微信朋友圈(?!.*(?:九宫格|小图|小屏|列表|入口|缩略图|小卡片|信息流|推荐位|图标位|宫格))/,
];

const SMALL_PATTERNS = [
  /小图/,
  /小屏/,
  /列表/,
  /入口/,
  /缩略图/,
  /小卡片/,
  /信息流/,
  /推荐位/,
  /图标位/,
  /宫格/,
];

const SCENE_PATTERNS = [
  /真实使用/,
  /使用场景/,
  /场景图/,
  /人物在用/,
  /家长看到/,
  /家长.*看到/,
  /看到.*学习结果/,
  /老师使用/,
  /孩子操作/,
  /课堂/,
  /书桌/,
  /手机查看/,
  /家里/,
];

const NON_SCENE_PATTERNS = [
  /图标/,
  /界面截图/,
  /功能卡片/,
  /流程图/,
  /纯排版/,
  /数据面板/,
  /\bui\b/i,
  /示意图/,
];

export function understandImageChannelIntent(
  query: string,
  entries: ChannelIntentEntry[] = DEFAULT_CHANNEL_INTENT_ENTRIES,
): ImageChannelIntent | null {
  const normalized = query.trim();
  if (!normalized) return null;

  const entryMatch = findEntryMatch(normalized, entries);
  const familyMatch = FAMILY_PATTERNS
    .map((candidate) => ({
      family: candidate.family,
      evidence: collectEvidence(normalized, candidate.patterns),
    }))
    .find((candidate) => candidate.evidence.length > 0);

  if (!entryMatch && !familyMatch) return null;

  const largeEvidence = collectEvidence(normalized, LARGE_PATTERNS);
  const smallEvidence = collectEvidence(normalized, SMALL_PATTERNS);
  const family = entryMatch?.entry.family ?? familyMatch?.family;
  if (!family) return null;
  const channelSize = sizeFromEvidence(
    entryMatch?.entry.size === 'large' ? [...largeEvidence, ...entryMatch.evidence] : largeEvidence,
    entryMatch?.entry.size === 'small' ? [...smallEvidence, ...entryMatch.evidence] : smallEvidence,
  );
  const sceneEvidence = collectEvidence(normalized, SCENE_PATTERNS);
  const nonSceneEvidence = collectEvidence(normalized, NON_SCENE_PATTERNS);
  const scenePreference = sceneFromEvidence(sceneEvidence, nonSceneEvidence);
  const candidateChannels = entryMatch
    ? [entryMatch.entry.value]
    : candidateChannelsFor(family, channelSize);
  const exactChannel = candidateChannels.length === 1 ? candidateChannels[0] : null;
  const confidence = confidenceFor(entryMatch?.evidence ?? familyMatch?.evidence ?? [], channelSize, scenePreference);
  const evidence = unique([
    ...(entryMatch?.evidence ?? []),
    ...(familyMatch?.evidence ?? []),
    ...largeEvidence,
    ...smallEvidence,
    ...sceneEvidence,
    ...nonSceneEvidence,
  ]);

  return {
    channelFamily: family,
    channelSize,
    exactChannel,
    candidateChannels,
    scenePreference,
    confidence,
    evidence,
    recommendation: buildRecommendation({
      family,
      exactChannel,
      candidateChannels,
      query: normalized,
      recommendationDescription: entryMatch?.entry.recommendationDescription,
    }),
  };
}

export function channelIntentLabel(intent: ImageChannelIntent | null | undefined): string {
  if (!intent) return '';
  if (intent.exactChannel) return intent.exactChannel;
  return CHANNEL_FAMILY_LABELS[intent.channelFamily];
}

function candidateChannelsFor(
  family: Exclude<ChannelFamily, 'unknown'>,
  size: ChannelSize,
): string[] {
  if (family === 'mobile') {
    if (size === 'large') return ['手机端大图'];
    if (size === 'small') return ['手机端小图'];
  }
  if (family === 'website') {
    if (size === 'large') return ['官网大图'];
    if (size === 'small') return ['官网小图'];
  }
  return FAMILY_CANDIDATES[family];
}

function sizeFromEvidence(largeEvidence: string[], smallEvidence: string[]): ChannelSize {
  if (largeEvidence.length > 0 && smallEvidence.length === 0) return 'large';
  if (smallEvidence.length > 0 && largeEvidence.length === 0) return 'small';
  return 'unspecified';
}

function sceneFromEvidence(sceneEvidence: string[], nonSceneEvidence: string[]): ScenePreference {
  if (sceneEvidence.length > 0 && nonSceneEvidence.length === 0) return 'scene';
  if (nonSceneEvidence.length > 0 && sceneEvidence.length === 0) return 'non_scene';
  return 'unspecified';
}

function confidenceFor(
  familyEvidence: string[],
  channelSize: ChannelSize,
  scenePreference: ScenePreference,
): IntentConfidence {
  if (familyEvidence.length > 0 && channelSize !== 'unspecified') return 'high';
  if (familyEvidence.length > 0 && scenePreference !== 'unspecified') return 'high';
  if (familyEvidence.length > 0) return 'medium';
  return 'low';
}

function buildRecommendation({
  family,
  exactChannel,
  candidateChannels,
  query,
  recommendationDescription,
}: {
  family: Exclude<ChannelFamily, 'unknown'>;
  exactChannel: string | null;
  candidateChannels: string[];
  query: string;
  recommendationDescription?: string;
}): string {
  if (exactChannel) {
    const recommendation = channelRecommendationFor(exactChannel);
    const detail = recommendationDescription ?? recommendation?.description ?? '这类渠道需要素材和使用位置保持一致。';
    return `推荐用于${exactChannel}：${detail}这次需求提到了“${shortQuery(query)}”，结果会优先保留更符合该渠道语境的素材。`;
  }
  if (family === 'mobile') {
    return `已理解为手机端使用场景：如果是首屏或重点宣传位，更适合手机端大图；如果是列表、入口或小屏推荐位，更适合手机端小图。当前先同时保留${candidateChannels.join('和')}，并优先推荐缩小后仍容易识别的素材。`;
  }
  if (family === 'website') {
    return `已理解为官网使用场景：如果是首页首屏或主视觉，更适合官网大图；如果是模块、列表或功能入口，更适合官网小图。当前先同时保留${candidateChannels.join('和')}，方便继续比较。`;
  }
  return `推荐用于${CHANNEL_FAMILY_LABELS[family]}：这次需求提到了“${shortQuery(query)}”，结果会优先保留适合该渠道讲述和展示的素材。`;
}

function collectEvidence(input: string, patterns: RegExp[]): string[] {
  return unique(patterns.flatMap((pattern) => {
    const match = input.match(pattern);
    return match?.[0] ? [match[0]] : [];
  }));
}

function findEntryMatch(input: string, entries: ChannelIntentEntry[]) {
  return entries
    .map((entry) => ({
      entry,
      evidence: entry.phrases.filter((phrase) => phraseMatches(input, phrase)),
    }))
    .find((candidate) => candidate.evidence.length > 0);
}

function phraseMatches(input: string, phrase: string): boolean {
  const normalizedPhrase = phrase.trim();
  if (!normalizedPhrase) return false;
  return input.toLocaleLowerCase().includes(normalizedPhrase.toLocaleLowerCase());
}

function unique(items: string[]): string[] {
  return [...new Set(items.filter(Boolean))];
}

function shortQuery(query: string): string {
  return query.length <= 24 ? query : `${query.slice(0, 24)}...`;
}

export function isKnownChannel(channel: string): boolean {
  return CHANNEL_VALUES.includes(channel);
}
