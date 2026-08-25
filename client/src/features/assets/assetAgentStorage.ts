const LEGACY_ASSET_AGENT_STORAGE_KEYS = [
  'piancton.assetAgent.sessions.v1',
  'piancton.assetAgent.session.v1',
  'piancton.assetAgent.chat.v1',
  'piancton.assetAgent.state.v1',
] as const;

export function clearLegacyAssetAgentStorage(
  storage: Pick<Storage, 'removeItem'> = window.localStorage,
): void {
  for (const key of LEGACY_ASSET_AGENT_STORAGE_KEYS) {
    storage.removeItem(key);
  }
}
