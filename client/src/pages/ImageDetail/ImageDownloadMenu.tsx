import { ChevronDown, Download } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@client/src/components/ui/dropdown-menu';
import { variantLabel } from '@client/src/features/assets/assetPresentation';
import type { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import type { AssetImage, ImageDetail } from '@client/src/types/api';

type ImageDetailActions = ReturnType<typeof useImageDetailActions>;

interface ImageDownloadMenuProps {
  detail: ImageDetail;
  variants?: AssetImage[];
  actions: ImageDetailActions;
}

function ImageDownloadMenu({ detail, variants = [], actions }: ImageDownloadMenuProps) {
  const current = variants.find((variant) => variant.id === detail.id) ?? detailToVariant(detail);
  const availableVersions = uniqueById([current, ...variants.filter((variant) => variant.isCurrent)]);
  const otherVersions = availableVersions.filter((variant) => variant.id !== current.id);

  if (availableVersions.length <= 1) {
    return (
      <Button
        className="w-full bg-foreground text-background hover:bg-foreground/88"
        disabled={actions.downloading}
        onClick={actions.download}
      >
        <Download className="size-4" />下载当前尺寸
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          className="w-full justify-between bg-foreground text-background hover:bg-foreground/88"
          disabled={actions.downloading}
        >
          <span className="inline-flex items-center gap-2">
            <Download className="size-4" />下载当前尺寸
          </span>
          <ChevronDown className="size-4 opacity-75" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72 rounded-xl p-1.5">
        <DropdownMenuLabel className="px-2.5 py-2 text-xs text-muted-foreground">
          选择要下载的素材尺寸
        </DropdownMenuLabel>
        <DropdownMenuItem
          className="rounded-lg px-2.5 py-2"
          onClick={() => actions.downloadTarget(current)}
        >
          <Download className="size-4" />
          <span className="min-w-0 flex-1 truncate">当前尺寸</span>
          <span className="shrink-0 text-xs text-muted-foreground">{compactVariantLabel(current)}</span>
        </DropdownMenuItem>
        {otherVersions.length > 0 && (
          <DropdownMenuSub>
            <DropdownMenuSubTrigger className="rounded-lg px-2.5 py-2">
              选择其他尺寸
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent className="w-72 rounded-xl p-1.5">
              {otherVersions.map((variant) => (
                <DropdownMenuItem
                  key={variant.id}
                  className="rounded-lg px-2.5 py-2"
                  onClick={() => actions.downloadTarget(variant)}
                >
                  <span className="min-w-0 flex-1 truncate">{variant.title}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">{compactVariantLabel(variant)}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuSubContent>
          </DropdownMenuSub>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="rounded-lg px-2.5 py-2"
          onClick={() => actions.downloadAll(availableVersions)}
        >
          <Download className="size-4" />
          全部下载
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function detailToVariant(detail: ImageDetail): AssetImage {
  return {
    id: detail.id,
    title: detail.title,
    fileName: detail.fileName,
    thumbnailUrl: detail.thumbnailUrl,
    contentUrl: detail.contentUrl,
    downloadUrl: detail.downloadUrl,
    assetRole: detail.assetRole,
    width: detail.width,
    height: detail.height,
    aspectRatio: detail.aspectRatio,
    channel: detail.channel,
    versionNo: detail.versionNo,
    isCurrent: detail.isCurrent,
  };
}

function uniqueById(variants: AssetImage[]): AssetImage[] {
  return Array.from(new Map(variants.map((variant) => [variant.id, variant])).values());
}

function compactVariantLabel(variant: AssetImage): string {
  return variantLabel(variant).replace(/^主图 · /, '').replace(/^延展 · /, '');
}

export default ImageDownloadMenu;
