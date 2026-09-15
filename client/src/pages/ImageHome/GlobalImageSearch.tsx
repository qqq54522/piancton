import { ArrowUpDown, Bell, BriefcaseBusiness, Check, Film, FolderHeart, Heart, LogOut, MessageSquarePlus, Plus, SlidersHorizontal, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Avatar, AvatarFallback } from '@client/src/components/ui/avatar';
import { Button } from '@client/src/components/ui/button';
import FeedbackDialog from '@client/src/components/FeedbackDialog';
import HorizontalScrollRail from '@client/src/components/HorizontalScrollRail';
import { PianctonAgentMark } from '@client/src/components/PianctonAgentMark';
import UnreadAnnouncementBadge from '@client/src/components/UnreadAnnouncementBadge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@client/src/components/ui/dropdown-menu';
import { useAuth } from '@client/src/lib/auth';
import { useAnnouncementUnreadCount } from '@client/src/features/announcements/useAnnouncements';
import {
  type SceneImageFilter,
  type SearchRefinementOptions,
  type SearchRefinements,
} from './searchResultFilters';
import { useChannelOptions } from './channelOptions';

interface GlobalImageSearchProps {
  refinementOptions: SearchRefinementOptions;
  refinements: SearchRefinements;
  sortBy: 'createdAt' | 'downloadCount';
  showBusinessAccount: boolean;
  manualFilterOpen: boolean;
  animateGifPreview: boolean;
  agentOpen: boolean;
  onChannelChange: (value: string) => void;
  onSceneChange: (value: SceneImageFilter) => void;
  onSortByChange: (value: 'createdAt' | 'downloadCount') => void;
  onManualFilterOpenChange: (open: boolean) => void;
  onAnimateGifPreviewChange: (value: boolean) => void;
  onAgentOpenChange: (open: boolean) => void;
}

const GlobalImageSearch = ({
  refinementOptions,
  refinements,
  sortBy,
  showBusinessAccount,
  manualFilterOpen,
  animateGifPreview,
  agentOpen,
  onChannelChange,
  onSceneChange,
  onSortByChange,
  onManualFilterOpenChange,
  onAnimateGifPreviewChange,
  onAgentOpenChange,
}: GlobalImageSearchProps) => {
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const channelOptions = useChannelOptions(refinementOptions.channels);
  const canAddChannel = !showBusinessAccount;
  const unreadAnnouncements = useAnnouncementUnreadCount(showBusinessAccount);
  const unreadCount = unreadAnnouncements.data?.unreadCount ?? 0;
  const intentChannels = refinements.channel
    ? []
    : refinements.channelIntent?.candidateChannels ?? [];
  const forYouSelected = showBusinessAccount
    && !refinements.channel
    && intentChannels.length === 0;

  const sceneSelected = refinements.scene === 'scene';
  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };


  return (
    <section className="min-w-0">
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} />

      <div className="flex min-w-0 items-center gap-3">
        <button
            type="button"
            aria-expanded={manualFilterOpen}
            aria-label={manualFilterOpen ? '收起渠道分类' : '展开渠道分类'}
            onClick={() => onManualFilterOpenChange(!manualFilterOpen)}
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl shadow-sm transition ${manualFilterOpen ? 'bg-foreground text-background' : 'bg-white text-foreground ring-1 ring-border/70 hover:bg-[#f1f1ef]'}`}
            title={refinements.channel ? `${refinements.channel}的分类` : '业务卖点筛选'}
          >
            <SlidersHorizontal className="size-4" />
          </button>
        <HorizontalScrollRail
          className="flex min-w-0 flex-1 items-center gap-4 overflow-x-auto pb-2 pr-2"
          aria-label="按使用渠道筛选"
          title="滚动滚轮或按住鼠标左右拖动查看更多渠道"
        >
          <button
            type="button"
            className={`relative h-10 shrink-0 px-0 text-sm font-semibold transition-colors after:absolute after:bottom-0 after:left-0 after:h-[3px] after:w-full after:rounded-full after:transition-opacity ${refinements.channel || intentChannels.length > 0 ? 'text-muted-foreground after:bg-transparent hover:text-foreground' : 'text-foreground after:bg-foreground'}`}
            onClick={() => onChannelChange('')}
          >
            猜你喜欢
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
          {canAddChannel && (
            <Button type="button" variant="ghost" size="sm"
              className="h-10 shrink-0 rounded-none px-0 font-semibold text-muted-foreground"
              onClick={() => navigate('/admin/channels')}>
              <Plus className="size-3.5" />管理渠道
            </Button>
          )}
        </HorizontalScrollRail>
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
          {forYouSelected ? (
            <span className="inline-flex h-8 items-center gap-2 rounded-full border border-border bg-white px-3 text-xs font-medium text-foreground shadow-xs">
              <Sparkles className="size-3.5" />
              个性优先
            </span>
          ) : (
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
          )}
          {showBusinessAccount && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button type="button" aria-label="打开账号菜单" className="relative flex size-10 shrink-0 items-center justify-center rounded-full border border-border bg-white">
                  <Avatar className="size-8 border border-border bg-[#f1f1ef]"><AvatarFallback className="bg-[#f1f1ef]"><BriefcaseBusiness className="size-4" /></AvatarFallback></Avatar>
                  <UnreadAnnouncementBadge count={unreadCount} />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52 rounded-xl p-1.5">
                <DropdownMenuLabel><span className="block text-xs font-semibold">{user?.username}</span><span className="text-[11px] font-normal text-muted-foreground">业务用户</span></DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate('/my-likes')}><Heart className="size-4" />我的喜欢</DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate('/my-collections')}><FolderHeart className="size-4" />我的收藏</DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate('/my-messages')}><Bell className="size-4" />我的信息{unreadCount > 0 && <span className="ml-auto text-red-500">{unreadCount}</span>}</DropdownMenuItem>
                <DropdownMenuItem onClick={() => setFeedbackOpen(true)}><MessageSquarePlus className="size-4" />提交反馈</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => void handleLogout()}><LogOut className="size-4" />退出并切换账号</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          <button type="button" className="flex size-9 items-center justify-center rounded-full border border-border bg-white lg:hidden"
            aria-label={agentOpen ? '收起 Piancton Agent' : '打开 Piancton Agent'}
            onClick={() => onAgentOpenChange(!agentOpen)}>
            <PianctonAgentMark size="sm" state={agentOpen ? 'wake' : 'idle'} interactive={false} className="!size-7" />
          </button>
        </div>
      </div>
    </section>
  );
};

export default GlobalImageSearch;
