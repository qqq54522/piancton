import { ArrowUpDown, BriefcaseBusiness, Check, Film, LogOut, Plus, Search, SlidersHorizontal, X } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Avatar, AvatarFallback } from '@client/src/components/ui/avatar';
import { Button } from '@client/src/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@client/src/components/ui/dropdown-menu';
import { Input } from '@client/src/components/ui/input';
import { shouldIgnoreEnterForIme } from '@client/src/lib/ime';
import { useAuth } from '@client/src/lib/auth';
import {
  type SceneImageFilter,
  type SearchRefinementOptions,
  type SearchRefinements,
} from './searchResultFilters';
import { addCustomChannel, useChannelOptions } from './channelOptions';

interface GlobalImageSearchProps {
  input: string;
  refinementOptions: SearchRefinementOptions;
  refinements: SearchRefinements;
  refinementsReady: boolean;
  sortBy: 'createdAt' | 'downloadCount';
  showBusinessAccount: boolean;
  manualFilterOpen: boolean;
  animateGifPreview: boolean;
  onInputChange: (value: string) => void;
  onChannelChange: (value: string) => void;
  onSceneChange: (value: SceneImageFilter) => void;
  onSortByChange: (value: 'createdAt' | 'downloadCount') => void;
  onManualFilterOpenChange: (open: boolean) => void;
  onAnimateGifPreviewChange: (value: boolean) => void;
  onClear: () => void;
  onSearch: (value?: string) => void;
}

const GlobalImageSearch = ({
  input,
  refinementOptions,
  refinements,
  sortBy,
  showBusinessAccount,
  manualFilterOpen,
  animateGifPreview,
  onInputChange,
  onChannelChange,
  onSceneChange,
  onSortByChange,
  onManualFilterOpenChange,
  onAnimateGifPreviewChange,
  onClear,
  onSearch,
}: GlobalImageSearchProps) => {
  const [addingChannel, setAddingChannel] = useState(false);
  const [draftChannel, setDraftChannel] = useState('');
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const channelOptions = useChannelOptions(refinementOptions.channels);
  const canAddChannel = !showBusinessAccount;
  const intentChannels = refinements.channel
    ? []
    : refinements.channelIntent?.candidateChannels ?? [];

  const sceneSelected = refinements.scene === 'scene';
  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };
  const submitCustomChannel = () => {
    const channel = addCustomChannel(draftChannel);
    if (!channel) return;
    setDraftChannel('');
    setAddingChannel(false);
    onChannelChange(channel);
  };

  return (
    <section className="mt-5 space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-5 top-1/2 size-5 -translate-y-1/2 text-foreground/55" />
          <Input
            aria-label="搜索业务素材"
            placeholder="搜索素材，或粘贴素材码/版本码/分享链接"
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={(event) => {
              if (shouldIgnoreEnterForIme(event)) return;
              if (event.key === 'Enter') onSearch();
            }}
            className="h-14 rounded-[22px] border-transparent bg-[#f1f1ef] pl-12 pr-32 text-base shadow-none transition-colors hover:bg-[#ececea] focus-visible:border-transparent focus-visible:bg-white focus-visible:ring-3 focus-visible:ring-foreground/10 md:text-base"
          />
          {input && (
            <button
              type="button"
              aria-label="清空搜索"
              onClick={onClear}
              className="absolute right-24 top-1/2 z-10 flex size-8 -translate-y-1/2 items-center justify-center rounded-full text-foreground/55 transition-colors hover:bg-black/5 hover:text-foreground"
            >
              <X className="size-4" />
            </button>
          )}
          <button
            type="button"
            onClick={() => onSearch()}
            className="absolute right-2 top-1/2 z-10 flex h-10 -translate-y-1/2 items-center rounded-[18px] bg-foreground px-4 text-sm font-semibold text-background shadow-sm transition hover:bg-foreground/88 active:translate-y-[calc(-50%+1px)]"
          >
            搜索
          </button>
        </div>
        {showBusinessAccount && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-border/70 bg-white shadow-xs transition-colors hover:bg-[#f1f1ef]"
                aria-label="打开账号菜单"
              >
                <Avatar className="size-9 border border-border bg-[#f1f1ef]">
                  <AvatarFallback className="bg-[#f1f1ef] text-foreground">
                    <BriefcaseBusiness className="size-4" />
                  </AvatarFallback>
                </Avatar>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52 rounded-xl p-1.5">
              <DropdownMenuLabel className="px-2.5 py-2">
                <span className="block text-xs font-semibold">{user?.username}</span>
                <span className="mt-0.5 block text-[11px] font-normal text-muted-foreground">当前身份：业务用户</span>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="rounded-lg px-2.5 py-2" onClick={handleLogout}>
                <LogOut className="size-4" />退出并切换账号
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
        <div
          className="flex min-w-0 items-center gap-4 overflow-x-auto pb-1 pr-2"
          aria-label="按使用渠道筛选"
        >
          <button
            type="button"
            aria-expanded={manualFilterOpen}
            aria-label={manualFilterOpen ? '收起卖点筛选' : '展开卖点筛选'}
            onClick={() => onManualFilterOpenChange(!manualFilterOpen)}
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl shadow-sm transition ${manualFilterOpen ? 'bg-foreground text-background' : 'bg-white text-foreground ring-1 ring-border/70 hover:bg-[#f1f1ef]'}`}
            title="展开卖点筛选"
          >
            <SlidersHorizontal className="size-4" />
          </button>
          <button
            type="button"
            className={`relative h-10 shrink-0 px-0 text-sm font-semibold transition-colors after:absolute after:bottom-0 after:left-0 after:h-[3px] after:w-full after:rounded-full after:transition-opacity ${refinements.channel || intentChannels.length > 0 ? 'text-muted-foreground after:bg-transparent hover:text-foreground' : 'text-foreground after:bg-foreground'}`}
            onClick={() => onChannelChange('')}
          >
            全部渠道
          </button>
          {channelOptions.map((channel) => (
            <button
              key={channel}
              type="button"
              className={`relative h-10 shrink-0 px-0 text-sm font-semibold transition-colors after:absolute after:bottom-0 after:left-0 after:h-[3px] after:w-full after:rounded-full after:transition-opacity ${refinements.channel === channel || intentChannels.includes(channel) ? 'text-foreground after:bg-foreground' : 'text-muted-foreground after:bg-transparent hover:text-foreground'}`}
              onClick={() => onChannelChange(channel)}
            >
              {channel}
            </button>
          ))}
          {canAddChannel && addingChannel ? (
            <div className="flex min-w-44 shrink-0 items-center gap-1 rounded-xl border border-border bg-white px-2 py-1">
              <Input
                value={draftChannel}
                onChange={(event) => setDraftChannel(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') submitCustomChannel();
                  if (event.key === 'Escape') {
                    setDraftChannel('');
                    setAddingChannel(false);
                  }
                }}
                placeholder="新增渠道"
                maxLength={24}
                className="h-7 border-0 bg-transparent px-1 text-xs shadow-none focus-visible:ring-0"
                autoFocus
              />
              <Button
                type="button"
                size="sm"
                className="h-7 bg-foreground px-2 text-xs text-background hover:bg-foreground/88"
                disabled={!draftChannel.trim()}
                onClick={submitCustomChannel}
              >
                添加
              </Button>
              <button
                type="button"
                aria-label="取消新增渠道"
                onClick={() => {
                  setDraftChannel('');
                  setAddingChannel(false);
                }}
                className="flex size-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <X className="size-3.5" />
              </button>
            </div>
          ) : canAddChannel ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-10 shrink-0 rounded-none px-0 font-semibold text-muted-foreground shadow-none hover:bg-transparent hover:text-foreground"
              onClick={() => setAddingChannel(true)}
            >
              <Plus className="size-3.5" />添加渠道
            </Button>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center justify-end gap-2">
          <button
            type="button"
            role="switch"
            aria-label="动图预览"
            aria-checked={animateGifPreview}
            onClick={() => onAnimateGifPreviewChange(!animateGifPreview)}
            className={`inline-flex h-8 items-center gap-2 rounded-full border px-3 text-xs font-medium transition-colors ${animateGifPreview ? 'border-foreground bg-foreground text-background shadow-sm' : 'border-border bg-white text-foreground shadow-xs hover:bg-[#f1f1ef]'}`}
          >
            <Film className="size-3.5" />
            动图预览
          </button>
          <button
            type="button"
            role="switch"
            aria-label="按场景图筛选"
            aria-checked={sceneSelected}
            onClick={() => onSceneChange(sceneSelected ? 'all' : 'scene')}
            className={`inline-flex h-8 items-center gap-2 rounded-full border px-3 text-xs font-medium transition-colors ${sceneSelected ? 'border-foreground bg-foreground text-background shadow-sm' : 'border-border bg-white text-foreground shadow-xs hover:bg-[#f1f1ef]'}`}
          >
            <span className={`relative h-4 w-8 shrink-0 rounded-full transition-colors ${sceneSelected ? 'bg-white/25' : 'bg-[#e5e5e1]'}`}>
              <span className={`absolute left-0 top-0.5 size-3 rounded-full bg-white shadow-sm transition-transform ${sceneSelected ? 'translate-x-[18px]' : 'translate-x-0.5'}`} />
            </span>
            场景图
          </button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="rounded-full bg-white">
                <ArrowUpDown className="size-4" />
                {sortBy === 'downloadCount' ? '下载较多' : '最近上传'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40 rounded-xl p-1.5">
              <DropdownMenuItem className="justify-between rounded-lg" onClick={() => onSortByChange('createdAt')}>
                <span>最近上传</span>
                {sortBy === 'createdAt' && <Check className="size-4" />}
              </DropdownMenuItem>
              <DropdownMenuItem className="justify-between rounded-lg" onClick={() => onSortByChange('downloadCount')}>
                <span>下载较多</span>
                {sortBy === 'downloadCount' && <Check className="size-4" />}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </section>
  );
};

export default GlobalImageSearch;
