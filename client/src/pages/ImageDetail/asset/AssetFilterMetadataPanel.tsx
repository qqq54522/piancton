import { useEffect, useMemo, useState } from 'react';
import { Loader2, Plus, Save, X } from 'lucide-react';
import { toast } from 'sonner';

import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import type { useAssetActions } from '@client/src/features/assets/useAssetActions';
import { useImageChannelOptions } from '@client/src/features/images/hooks/useImageListQuery';
import type { AssetGroup } from '@client/src/types/api';
import { addCustomChannel, useChannelOptions } from '../../ImageHome/channelOptions';
import { joinChannelValues, splitChannelValue } from '../../ImageHome/channelValue';

type AssetActions = ReturnType<typeof useAssetActions>;

interface AssetFilterMetadataPanelProps {
  group: AssetGroup;
  currentImageId: string;
  actions: AssetActions;
}

function AssetFilterMetadataPanel({
  group,
  currentImageId,
  actions,
}: AssetFilterMetadataPanelProps) {
  const currentImage = useMemo(
    () => group.images.find((image) => image.id === currentImageId) ?? group.images[0],
    [currentImageId, group.images],
  );
  const initialChannels = splitChannelValue(currentImage?.channel);
  const initialChannelKey = initialChannels.join('|');
  const [selectedChannels, setSelectedChannels] = useState(initialChannels);
  const [styleLabel, setStyleLabel] = useState(group.styleLabel ?? '');
  const [isSceneImage, setIsSceneImage] = useState(group.isSceneImage === true);
  const [addingChannel, setAddingChannel] = useState(false);
  const [draftChannel, setDraftChannel] = useState('');
  const remoteChannels = useImageChannelOptions(Boolean(currentImage));
  const channelOptions = useChannelOptions([
    ...(remoteChannels.data?.channels ?? []),
    ...initialChannels,
  ]);

  useEffect(() => {
    setSelectedChannels(initialChannelKey ? initialChannelKey.split('|') : []);
    setStyleLabel(group.styleLabel ?? '');
    setIsSceneImage(group.isSceneImage === true);
  }, [group.isSceneImage, group.styleLabel, initialChannelKey]);

  if (!currentImage) return null;

  const addChannel = () => {
    const next = addCustomChannel(draftChannel);
    if (!next) return;
    setSelectedChannels((items) => [...new Set([...items, next])]);
    setDraftChannel('');
    setAddingChannel(false);
  };

  const save = async () => {
    if (selectedChannels.length === 0) {
      toast.error('请至少保留一个使用渠道');
      return;
    }
    try {
      await actions.updateFilterMetadata.mutateAsync({
        imageId: currentImage.id,
        channel: joinChannelValues(selectedChannels),
        styleLabel: styleLabel.trim() || null,
        isSceneImage,
      });
      toast.success('业务筛选信息已保存');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  const pending = actions.updateFilterMetadata.isPending;

  return (
    <section className="surface-card p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">业务筛选信息</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            渠道只修改当前查看版本；画面风格和场景图由同组横版、竖版共同使用。
          </p>
        </div>
        <Button size="sm" onClick={save} disabled={pending || selectedChannels.length === 0}>
          {pending ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
          保存筛选信息
        </Button>
      </div>

      <div className="space-y-4">
        <div>
          <span className="field-label">使用渠道</span>
          <div className="mt-1.5 flex flex-wrap gap-2">
            {channelOptions.map((channel) => (
              <Button
                key={channel}
                type="button"
                variant={selectedChannels.includes(channel) ? 'default' : 'outline'}
                size="sm"
                disabled={pending}
                className={selectedChannels.includes(channel) ? 'bg-foreground text-background hover:bg-foreground/88' : undefined}
                onClick={() => setSelectedChannels((items) => (
                  items.includes(channel)
                    ? items.filter((item) => item !== channel)
                    : [...items, channel]
                ))}
              >
                {channel}
              </Button>
            ))}
            {addingChannel ? (
              <div className="flex min-w-44 items-center gap-1 rounded-xl border border-border bg-white px-2 py-1">
                <Input
                  value={draftChannel}
                  onChange={(event) => setDraftChannel(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') addChannel();
                    if (event.key === 'Escape') setAddingChannel(false);
                  }}
                  placeholder="新增渠道"
                  maxLength={24}
                  className="h-7 border-0 bg-transparent px-1 text-xs shadow-none focus-visible:ring-0"
                  autoFocus
                />
                <Button type="button" size="sm" className="h-7 px-2 text-xs" disabled={!draftChannel.trim()} onClick={addChannel}>添加</Button>
                <button type="button" aria-label="取消新增渠道" className="flex size-7 items-center justify-center text-muted-foreground" onClick={() => setAddingChannel(false)}>
                  <X className="size-3.5" />
                </button>
              </div>
            ) : (
              <Button type="button" variant="outline" size="sm" onClick={() => setAddingChannel(true)}>
                <Plus className="size-3.5" />添加渠道
              </Button>
            )}
          </div>
        </div>

        <label className="block">
          <span className="field-label">画面风格</span>
          <Input
            value={styleLabel}
            maxLength={100}
            disabled={pending}
            placeholder="例如：官网风格、数据卡片、轻插画"
            onChange={(event) => setStyleLabel(event.target.value)}
          />
        </label>

        <div className="flex items-center gap-3">
          <span className="field-label mb-0">场景图</span>
          <button
            type="button"
            role="switch"
            aria-label="场景图"
            aria-checked={isSceneImage}
            disabled={pending}
            onClick={() => setIsSceneImage((value) => !value)}
            className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full border transition-colors disabled:opacity-50 ${isSceneImage ? 'border-foreground bg-foreground' : 'border-border bg-muted'}`}
          >
            <span className={`absolute left-1 size-5 rounded-full bg-white shadow-sm transition-transform ${isSceneImage ? 'translate-x-5' : 'translate-x-0'}`} />
          </button>
        </div>
      </div>
    </section>
  );
}

export default AssetFilterMetadataPanel;
