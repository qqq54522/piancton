export const CHANNEL_VALUE_SEPARATOR = '、';

export function splitChannelValue(value: string | null | undefined): string[] {
  return uniqueChannelValues((value ?? '').split(/[、,，/]/));
}

export function joinChannelValues(values: string[]): string {
  return uniqueChannelValues(values).join(CHANNEL_VALUE_SEPARATOR);
}

export function channelValueIncludes(value: string | null | undefined, channel: string): boolean {
  const normalized = channel.trim();
  return Boolean(normalized && splitChannelValue(value).includes(normalized));
}

function uniqueChannelValues(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  values.forEach((value) => {
    const channel = value.trim();
    if (!channel || seen.has(channel)) return;
    seen.add(channel);
    result.push(channel);
  });
  return result;
}
