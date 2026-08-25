import { useState, type ReactNode } from 'react';
import {
  Check,
  ExternalLink,
  FilePenLine,
  Link as LinkIcon,
  Pencil,
  Trash2,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import type { useAssetActions } from '@client/src/features/assets/useAssetActions';
import type { AssetGroup, AssetSourceLink, AssetSourceLinkType } from '@client/src/types/api';

type AssetActions = ReturnType<typeof useAssetActions>;

const LINK_TYPES: Array<{ value: AssetSourceLinkType; label: string }> = [
  { value: 'figma', label: 'Figma' },
  { value: 'design_file', label: '设计文件' },
  { value: 'cloud_drive', label: '网盘' },
  { value: 'reference_doc', label: '需求文档' },
  { value: 'asset_package', label: '素材包' },
  { value: 'other', label: '其他' },
];

const blankForm = {
  label: '',
  url: '',
  linkType: 'figma' as AssetSourceLinkType,
  note: '',
};

function AssetSourceLinksPanel({
  group,
  actions,
}: {
  group: AssetGroup;
  actions: AssetActions;
}) {
  const [form, setForm] = useState(blankForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState(blankForm);
  const sourceLinks = group.sourceLinks ?? [];

  const addLink = async () => {
    if (!form.label.trim() || !form.url.trim()) return;
    try {
      await actions.addSourceLink.mutateAsync({
        label: form.label.trim(),
        url: form.url.trim(),
        linkType: form.linkType,
        note: form.note.trim() || undefined,
      });
      setForm(blankForm);
      toast.success('设计源文件已添加');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  const startEditing = (link: AssetSourceLink) => {
    setEditingId(link.id);
    setEditForm({
      label: link.label,
      url: link.url,
      linkType: link.linkType,
      note: link.note ?? '',
    });
  };

  const saveEdit = async (linkId: string) => {
    if (!editForm.label.trim() || !editForm.url.trim()) return;
    try {
      await actions.updateSourceLink.mutateAsync({
        linkId,
        data: {
          label: editForm.label.trim(),
          url: editForm.url.trim(),
          linkType: editForm.linkType,
          note: editForm.note.trim() || null,
        },
      });
      setEditingId(null);
      toast.success('设计源文件已更新');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  const removeLink = async (linkId: string) => {
    try {
      await actions.deleteSourceLink.mutateAsync(linkId);
      toast.success('设计源文件已删除');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  return (
    <section className="surface-card p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">设计源文件</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            保存 Figma、网盘或需求文档等可追溯链接，方便后续改图。
          </p>
        </div>
        <span className="rounded-full bg-secondary px-2.5 py-1 text-[11px] text-muted-foreground">
          {sourceLinks.length} 条
        </span>
      </div>

      <div className="mt-4 space-y-2">
        {sourceLinks.length > 0 ? (
          sourceLinks.map((link) => {
            const isEditing = editingId === link.id;
            return (
              <div
                key={link.id}
                className="rounded-2xl border border-border/80 bg-card p-3.5"
              >
                {isEditing ? (
                  <SourceLinkForm
                    value={editForm}
                    onChange={setEditForm}
                    primaryAction={
                      <Button
                        size="sm"
                        onClick={() => saveEdit(link.id)}
                        disabled={
                          !editForm.label.trim()
                          || !editForm.url.trim()
                          || actions.updateSourceLink.isPending
                        }
                      >
                        <Check className="size-4" />保存
                      </Button>
                    }
                    secondaryAction={
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setEditingId(null)}
                      >
                        <X className="size-4" />取消
                      </Button>
                    }
                  />
                ) : (
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-xl bg-secondary text-muted-foreground">
                      <FilePenLine className="size-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="min-w-0 truncate text-sm font-semibold">{link.label}</h3>
                        <span className="rounded-full bg-secondary px-2 py-0.5 text-[11px] text-muted-foreground">
                          {typeLabel(link.linkType)}
                        </span>
                      </div>
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1 inline-flex max-w-full items-center gap-1 truncate text-xs text-primary hover:underline"
                      >
                        <LinkIcon className="size-3.5 shrink-0" />
                        <span className="truncate">{link.url}</span>
                        <ExternalLink className="size-3 shrink-0" />
                      </a>
                      {link.note && (
                        <p className="mt-1 text-xs leading-5 text-muted-foreground">{link.note}</p>
                      )}
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        title="编辑源文件链接"
                        aria-label={`编辑“${link.label}”`}
                        onClick={() => startEditing(link)}
                      >
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        title="删除源文件链接"
                        aria-label={`删除“${link.label}”`}
                        className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        disabled={actions.deleteSourceLink.isPending}
                        onClick={() => removeLink(link.id)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/30 px-4 py-6 text-center text-sm text-muted-foreground">
            还没有设计源文件链接
          </div>
        )}
      </div>

      <div className="mt-5 rounded-xl border border-border/80 bg-secondary/40 p-3">
        <SourceLinkForm
          value={form}
          onChange={setForm}
          primaryAction={
            <Button
              onClick={addLink}
              disabled={!form.label.trim() || !form.url.trim() || actions.addSourceLink.isPending}
            >
              <LinkIcon className="size-4" />添加
            </Button>
          }
        />
      </div>
    </section>
  );
}

function SourceLinkForm({
  value,
  onChange,
  primaryAction,
  secondaryAction,
}: {
  value: typeof blankForm;
  onChange: (value: typeof blankForm) => void;
  primaryAction: ReactNode;
  secondaryAction?: ReactNode;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-[150px_minmax(0,1fr)]">
      <label className="space-y-1">
        <span className="field-label">类型</span>
        <select
          value={value.linkType}
          onChange={(event) => onChange({
            ...value,
            linkType: event.target.value as AssetSourceLinkType,
          })}
          className="h-10 w-full rounded-xl border border-input bg-card px-3 text-sm outline-none transition-[border-color,box-shadow] enabled:hover:border-ring/50 focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/15"
        >
          {LINK_TYPES.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
      </label>
      <label className="space-y-1">
        <span className="field-label">名称</span>
        <Input
          value={value.label}
          onChange={(event) => onChange({ ...value, label: event.target.value })}
          placeholder="例如：Figma 源文件"
          maxLength={120}
        />
      </label>
      <label className="space-y-1 md:col-span-2">
        <span className="field-label">链接</span>
        <Input
          type="url"
          value={value.url}
          onChange={(event) => onChange({ ...value, url: event.target.value })}
          placeholder="https://..."
          maxLength={2048}
        />
      </label>
      <label className="space-y-1 md:col-span-2">
        <span className="field-label">备注</span>
        <textarea
          value={value.note}
          onChange={(event) => onChange({ ...value, note: event.target.value })}
          placeholder="例如：需设计组权限，画板在第 3 页"
          maxLength={500}
          rows={2}
          className="min-h-20 w-full resize-y rounded-xl border border-input bg-card px-3.5 py-2 text-sm shadow-xs outline-none transition-[border-color,box-shadow,background-color] placeholder:text-muted-foreground enabled:hover:border-ring/50 focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/15"
        />
      </label>
      <div className="flex flex-wrap justify-end gap-2 md:col-span-2">
        {secondaryAction}
        {primaryAction}
      </div>
    </div>
  );
}

function typeLabel(value: AssetSourceLinkType) {
  return LINK_TYPES.find((item) => item.value === value)?.label ?? '其他';
}

export default AssetSourceLinksPanel;
