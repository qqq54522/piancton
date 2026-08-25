export const ASSET_AGENT_ADD_IMAGE_EVENT = 'piancton:asset-agent-add-image';

export interface AssetAgentImagePayload {
  imageId: string;
  assetGroupId?: string | null;
  title: string;
}

export function sendImageToAssetAgent(payload: AssetAgentImagePayload) {
  window.dispatchEvent(
    new CustomEvent<AssetAgentImagePayload>(ASSET_AGENT_ADD_IMAGE_EVENT, {
      detail: payload,
    }),
  );
}

export function listenForAssetAgentImages(
  callback: (payload: AssetAgentImagePayload) => void,
) {
  const listener = (event: Event) => {
    const customEvent = event as CustomEvent<AssetAgentImagePayload>;
    if (customEvent.detail?.imageId) callback(customEvent.detail);
  };
  window.addEventListener(ASSET_AGENT_ADD_IMAGE_EVENT, listener);
  return () => window.removeEventListener(ASSET_AGENT_ADD_IMAGE_EVENT, listener);
}
