import { useMemo } from 'react';

import { addChannelIntentEntry, useChannelIntentValues } from './channelIntentCatalog';

const CUSTOM_CHANNEL_STORAGE_KEY = 'piancton.customChannels.v1';
const CUSTOM_CHANNELS_EVENT = 'piancton-custom-channels-changed';

function normalizeChannel(value: string) {
  return value.trim().replace(/\s+/g, ' ').slice(0, 24);
}

function uniqueChannels(values: string[]) {
  const seen = new Set<string>();
  const result: string[] = [];
  values.forEach((value) => {
    const channel = normalizeChannel(value);
    if (!channel || seen.has(channel)) return;
    seen.add(channel);
    result.push(channel);
  });
  return result;
}

function readCustomChannels() {
  try {
    const raw = window.localStorage.getItem(CUSTOM_CHANNEL_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? uniqueChannels(parsed.filter((item) => typeof item === 'string')) : [];
  } catch {
    return [];
  }
}

function writeCustomChannels(channels: string[]) {
  window.localStorage.setItem(CUSTOM_CHANNEL_STORAGE_KEY, JSON.stringify(uniqueChannels(channels)));
  window.dispatchEvent(new Event(CUSTOM_CHANNELS_EVENT));
}

export function addCustomChannel(value: string) {
  const channel = normalizeChannel(value);
  if (!channel) return '';
  const nextChannels = uniqueChannels([...readCustomChannels(), channel]);
  writeCustomChannels(nextChannels);
  addChannelIntentEntry(channel);
  return channel;
}

export function useChannelOptions(extraChannels: string[] = []) {
  const managedChannels = useChannelIntentValues();
  void extraChannels;

  return useMemo(
    () => uniqueChannels(managedChannels),
    [managedChannels],
  );
}
