import { useEffect, useMemo, useState } from 'react';

import {
  DEFAULT_CHANNEL_INTENT_ENTRIES,
  type ImageChannelIntent,
  type ChannelFamily,
  type ChannelIntentEntry,
  type ChannelSize,
} from './channelIntent';
import { channelRecommendationFor } from './channelRecommendations';

const CHANNEL_INTENT_STORAGE_KEY = 'piancton.channelIntentEntries.v1';
const CHANNEL_INTENT_EVENT = 'piancton-channel-intent-entries-changed';

export const CHANNEL_FAMILY_OPTIONS: Array<{ value: Exclude<ChannelFamily, 'unknown'>; label: string }> = [
  { value: 'ppt', label: 'PPT' },
  { value: 'brand_manual', label: '品牌手册' },
  { value: 'mobile', label: '手机端' },
  { value: 'website', label: '官网' },
];

export const CHANNEL_SIZE_OPTIONS: Array<{ value: ChannelSize; label: string }> = [
  { value: 'unspecified', label: '不区分' },
  { value: 'large', label: '大图' },
  { value: 'small', label: '小图' },
];

export function useChannelIntentEntries() {
  const [entries, setEntries] = useState<ChannelIntentEntry[]>(() => readChannelIntentEntries());

  useEffect(() => {
    const handleChange = () => setEntries(readChannelIntentEntries());
    window.addEventListener(CHANNEL_INTENT_EVENT, handleChange);
    window.addEventListener('storage', handleChange);
    return () => {
      window.removeEventListener(CHANNEL_INTENT_EVENT, handleChange);
      window.removeEventListener('storage', handleChange);
    };
  }, []);

  return entries;
}

export function useChannelIntentValues() {
  const entries = useChannelIntentEntries();
  return useMemo(() => entries.map((entry) => entry.value), [entries]);
}

export function isChannelIntentInCatalog(
  intent: ImageChannelIntent | null | undefined,
  entries: ChannelIntentEntry[],
) {
  if (!intent) return false;
  const entryValues = new Set(entries.map((entry) => entry.value));
  return intent.candidateChannels.length > 0
    && intent.candidateChannels.every((channel) => entryValues.has(channel));
}

export function readChannelIntentEntries(): ChannelIntentEntry[] {
  try {
    const raw = window.localStorage.getItem(CHANNEL_INTENT_STORAGE_KEY);
    if (!raw) return DEFAULT_CHANNEL_INTENT_ENTRIES;
    const parsed = JSON.parse(raw);
    return normalizeEntries(Array.isArray(parsed) ? parsed : DEFAULT_CHANNEL_INTENT_ENTRIES);
  } catch {
    return DEFAULT_CHANNEL_INTENT_ENTRIES;
  }
}

export function writeChannelIntentEntries(entries: ChannelIntentEntry[]) {
  const normalized = normalizeEntries(entries);
  window.localStorage.setItem(CHANNEL_INTENT_STORAGE_KEY, JSON.stringify(normalized));
  window.dispatchEvent(new Event(CHANNEL_INTENT_EVENT));
}

export function resetChannelIntentEntries() {
  writeChannelIntentEntries(DEFAULT_CHANNEL_INTENT_ENTRIES);
}

export function addChannelIntentEntry(value: string) {
  const label = normalizeLabel(value);
  if (!label) return '';
  const entries = readChannelIntentEntries();
  if (entries.some((entry) => entry.value === label)) return label;
  writeChannelIntentEntries([
    ...entries,
    {
      value: label,
      family: 'mobile',
      size: 'unspecified',
      phrases: suggestedPhrasesForChannel(label),
      recommendationDescription: generateRecommendationDescription({
        value: label,
        family: 'mobile',
        size: 'unspecified',
      }),
    },
  ]);
  return label;
}

export function removeChannelIntentEntry(value: string) {
  writeChannelIntentEntries(readChannelIntentEntries().filter((entry) => entry.value !== value));
}

export function updateChannelIntentEntry(
  value: string,
  patch: Partial<Pick<ChannelIntentEntry, 'family' | 'size' | 'phrases' | 'recommendationDescription'>>,
) {
  const entries = readChannelIntentEntries();
  writeChannelIntentEntries(entries.map((entry) => (
    entry.value === value ? { ...entry, ...patch } : entry
  )));
}

export function regenerateChannelRecommendation(value: string) {
  const entries = readChannelIntentEntries();
  writeChannelIntentEntries(entries.map((entry) => (
    entry.value === value
      ? { ...entry, recommendationDescription: generateRecommendationDescription(entry) }
      : entry
  )));
}

export function addChannelIntentPhrase(value: string, phrase: string) {
  const normalizedPhrase = normalizePhrase(phrase);
  if (!normalizedPhrase) return;
  const entries = readChannelIntentEntries();
  writeChannelIntentEntries(entries.map((entry) => (
    entry.value === value
      ? { ...entry, phrases: uniquePhrases([...entry.phrases, normalizedPhrase]) }
      : entry
  )));
}

export function removeChannelIntentPhrase(value: string, phrase: string) {
  const entries = readChannelIntentEntries();
  writeChannelIntentEntries(entries.map((entry) => (
    entry.value === value
      ? { ...entry, phrases: entry.phrases.filter((item) => item !== phrase) }
      : entry
  )));
}

function normalizeEntries(values: unknown[]): ChannelIntentEntry[] {
  const seen = new Set<string>();
  const result: ChannelIntentEntry[] = [];
  values.forEach((item) => {
    if (!isEntryLike(item)) return;
    const value = normalizeLabel(item.value);
    if (!value || seen.has(value)) return;
    seen.add(value);
    result.push({
      value,
      family: item.family,
      size: item.size,
      phrases: uniquePhrases([value, ...item.phrases]),
      recommendationDescription: normalizeRecommendation(
        item.recommendationDescription
          ?? channelRecommendationFor(value)?.description
          ?? generateRecommendationDescription({ value, family: item.family, size: item.size }),
      ),
    });
  });
  return result.length > 0 ? result : DEFAULT_CHANNEL_INTENT_ENTRIES;
}

function isEntryLike(item: unknown): item is ChannelIntentEntry {
  if (!item || typeof item !== 'object') return false;
  const candidate = item as ChannelIntentEntry;
  return typeof candidate.value === 'string'
    && ['ppt', 'brand_manual', 'mobile', 'website'].includes(candidate.family)
    && ['large', 'small', 'unspecified'].includes(candidate.size)
    && Array.isArray(candidate.phrases);
}

function normalizeLabel(value: string) {
  return value.trim().replace(/\s+/g, ' ').slice(0, 24);
}

function normalizePhrase(value: string) {
  return value.trim().replace(/\s+/g, ' ').slice(0, 48);
}

function normalizeRecommendation(value: string) {
  return value.trim().replace(/\s+/g, ' ').slice(0, 180);
}

function uniquePhrases(values: string[]) {
  const seen = new Set<string>();
  const result: string[] = [];
  values.forEach((value) => {
    const phrase = normalizePhrase(value);
    if (!phrase || seen.has(phrase)) return;
    seen.add(phrase);
    result.push(phrase);
  });
  return result;
}

function suggestedPhrasesForChannel(value: string) {
  return uniquePhrases([
    value,
    `用于${value}`,
    `放在${value}`,
    `${value}使用`,
    `${value}素材`,
  ]);
}

function generateRecommendationDescription(
  entry: Pick<ChannelIntentEntry, 'value' | 'family' | 'size'>,
) {
  const fixed = channelRecommendationFor(entry.value)?.description;
  if (fixed) return fixed;
  if (entry.family === 'ppt') {
    return `适合${entry.value}讲解和汇报，优先使用结构清楚、信息层级完整、能承接讲述节奏的素材。`;
  }
  if (entry.family === 'brand_manual') {
    return `适合${entry.value}沉淀标准表达，优先使用口径稳定、视觉规范、信息不依赖临时活动语境的素材。`;
  }
  if (entry.family === 'website') {
    return entry.size === 'small'
      ? `适合${entry.value}模块、列表或入口位置，优先使用缩小后仍清晰、核心信息单点明确的素材。`
      : `适合${entry.value}重点展示位置，优先使用视觉完成度高、场景完整、卖点明确的素材。`;
  }
  if (entry.size === 'small') {
    return `适合${entry.value}列表、入口或小屏推荐位，优先使用文字更少、主体更集中、用户能快速识别重点的素材。`;
  }
  if (entry.size === 'large') {
    return `适合${entry.value}首屏或重点位置，优先使用主体突出、标题直接、能在短时间建立卖点认知的素材。`;
  }
  return `适合${entry.value}使用场景，优先使用渠道语境清楚、主体明确、能帮助业务方快速判断可用性的素材。`;
}
