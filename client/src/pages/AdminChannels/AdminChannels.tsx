import { useMemo, useState } from 'react';
import { Plus, RotateCcw, Trash2, X } from 'lucide-react';
import { toast } from 'sonner';

import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { Select } from '@client/src/components/ui/select';
import {
  addChannelIntentEntry,
  addChannelIntentPhrase,
  CHANNEL_FAMILY_OPTIONS,
  CHANNEL_SIZE_OPTIONS,
  removeChannelIntentPhrase,
  removeChannelIntentEntry,
  regenerateChannelRecommendation,
  resetChannelIntentEntries,
  updateChannelIntentEntry,
  useChannelIntentEntries,
} from '@client/src/pages/ImageHome/channelIntentCatalog';
import type { ChannelIntentEntry } from '@client/src/pages/ImageHome/channelIntent';
import { channelRecommendationFor } from '@client/src/pages/ImageHome/channelRecommendations';

export default function AdminChannels() {
  const entries = useChannelIntentEntries();
  const [selectedValue, setSelectedValue] = useState(entries[0]?.value ?? '');
  const [draftChannel, setDraftChannel] = useState('');
  const selected = useMemo(
    () => entries.find((entry) => entry.value === selectedValue) ?? entries[0],
    [entries, selectedValue],
  );

  const addChannel = () => {
    const channel = addChannelIntentEntry(draftChannel);
    if (!channel) return;
    setDraftChannel('');
    setSelectedValue(channel);
    toast.success('渠道标签已添加');
  };

  return (
    <div className="page-shell">
      <PageHeader
        eyebrow="Channel Intent Language"
        title="场景与渠道管理"
        description="维护素材会被用在哪里，以及业务方可能怎么说这些渠道；搜索时会和卖点意图并行识别。"
      />

      <div className="mt-6 grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="surface-card p-3">
          <div className="mb-3 flex gap-2">
            <Input
              value={draftChannel}
              onChange={(event) => setDraftChannel(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') addChannel();
              }}
              placeholder="新增渠道标签"
              maxLength={24}
              className="h-9"
            />
            <Button size="icon" onClick={addChannel} disabled={!draftChannel.trim()}>
              <Plus className="size-4" />
            </Button>
          </div>
          <div className="space-y-1">
            {entries.map((entry) => (
              <button
                key={entry.value}
                type="button"
                onClick={() => setSelectedValue(entry.value)}
                className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition-colors ${selected?.value === entry.value ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-secondary hover:text-foreground'}`}
              >
                <span className="font-medium">{entry.value}</span>
                <span className="text-xs">{entry.phrases.length}</span>
              </button>
            ))}
          </div>
        </aside>

        {selected ? (
          <main className="surface-card p-5 sm:p-6">
            <div className="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-xl font-semibold tracking-tight">{selected.value}</h2>
                  <Badge variant="secondary">{familyLabel(selected.family)}</Badge>
                  <Badge variant="outline">{sizeLabel(selected.size)}</Badge>
                </div>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                  这些话术会帮助搜索框理解用户说的是哪个渠道；只说“手机端/官网”时仍会保留大图和小图两个候选。
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    resetChannelIntentEntries();
                    toast.success('已恢复默认渠道话术');
                  }}
                >
                  <RotateCcw className="size-4" />恢复默认
                </Button>
                <Button
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => {
                    removeChannelIntentEntry(selected.value);
                    toast.success('渠道标签已删除');
                  }}
                >
                  <Trash2 className="size-4" />删除渠道
                </Button>
              </div>
            </div>

            <ChannelMetaEditor entry={selected} />
            <ChannelRecommendationEditor entry={selected} />
            <ChannelPhraseEditor entry={selected} />
          </main>
        ) : (
          <div className="surface-card grid min-h-80 place-items-center text-sm text-muted-foreground">
            暂无渠道标签
          </div>
        )}
      </div>
    </div>
  );
}

function ChannelRecommendationEditor({ entry }: { entry: ChannelIntentEntry }) {
  const recommendation = entry.recommendationDescription ?? channelRecommendationFor(entry.value)?.description ?? '';
  return (
    <section className="mt-5 rounded-2xl border border-blue-100 bg-blue-50/70 p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-blue-950">搜索结果推荐说明</h3>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-white/70">业务方可见</Badge>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="bg-white/70"
            onClick={() => {
              regenerateChannelRecommendation(entry.value);
              toast.success('已按当前渠道语境重新生成推荐说明');
            }}
          >
            <RotateCcw className="size-3.5" />自动生成
          </Button>
        </div>
      </div>
      <textarea
        value={recommendation}
        onChange={(event) => updateChannelIntentEntry(entry.value, {
          recommendationDescription: event.target.value,
        })}
        maxLength={180}
        className="min-h-24 w-full resize-y rounded-xl border border-blue-100 bg-white/80 px-3 py-2 text-sm leading-6 text-blue-950 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
        placeholder="补充业务方看到的渠道推荐说明"
      />
      <p className="mt-2 text-xs text-blue-800/75">
        这段说明会出现在业务端搜索结果上方，用来解释为什么推荐这个渠道。
      </p>
    </section>
  );
}

function ChannelMetaEditor({ entry }: { entry: ChannelIntentEntry }) {
  return (
    <section className="mt-5 grid gap-3 rounded-2xl border border-border bg-card p-4 sm:grid-cols-2">
      <label>
        <span className="field-label">渠道家族</span>
        <Select
          value={entry.family}
          onChange={(event) => updateChannelIntentEntry(entry.value, {
            family: event.target.value as ChannelIntentEntry['family'],
          })}
        >
          {CHANNEL_FAMILY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </Select>
      </label>
      <label>
        <span className="field-label">尺寸语境</span>
        <Select
          value={entry.size}
          onChange={(event) => updateChannelIntentEntry(entry.value, {
            size: event.target.value as ChannelIntentEntry['size'],
          })}
        >
          {CHANNEL_SIZE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </Select>
      </label>
    </section>
  );
}

function ChannelPhraseEditor({ entry }: { entry: ChannelIntentEntry }) {
  const [draftPhrase, setDraftPhrase] = useState('');

  const addPhrase = () => {
    if (!draftPhrase.trim()) return;
    addChannelIntentPhrase(entry.value, draftPhrase);
    setDraftPhrase('');
    toast.success('渠道话术已添加');
  };

  return (
    <section className="mt-5 rounded-2xl border border-primary/15 bg-accent/45 p-4">
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          value={draftPhrase}
          onChange={(event) => setDraftPhrase(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') addPhrase();
          }}
          placeholder={`补充一种搜索“${entry.value}”的说法`}
          maxLength={48}
          className="bg-card sm:min-w-0 sm:flex-1"
        />
        <Button className="shrink-0" onClick={addPhrase} disabled={!draftPhrase.trim()}>
          <Plus className="size-4" />添加渠道话术
        </Button>
      </div>

      <div className="mt-4 rounded-2xl border border-border bg-card p-3">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold">已启用渠道话术 · {entry.phrases.length}</h3>
          <span className="text-xs text-muted-foreground">搜索框实时读取</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {entry.phrases.map((phrase) => (
            <span
              key={phrase}
              className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-primary/20 bg-primary/[0.06] px-3 py-1 text-xs text-primary"
            >
              <span className="min-w-0 break-words">{phrase}</span>
              {phrase !== entry.value && (
                <button
                  type="button"
                  aria-label={`删除渠道话术 ${phrase}`}
                  onClick={() => removeChannelIntentPhrase(entry.value, phrase)}
                  className="rounded-full p-0.5 text-primary/70 hover:bg-primary/10 hover:text-primary"
                >
                  <X className="size-3" />
                </button>
              )}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function familyLabel(value: ChannelIntentEntry['family']) {
  return CHANNEL_FAMILY_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

function sizeLabel(value: ChannelIntentEntry['size']) {
  return CHANNEL_SIZE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}
