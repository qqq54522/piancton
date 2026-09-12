import { type FormEvent, type ReactNode, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Loader2, Play, Plus, Power, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import {
  createApiCredential,
  deleteApiCredential,
  fetchApiCenterSummary,
  testApiCredential,
  updateApiCredential,
} from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { Select } from '@client/src/components/ui/select';
import type { ApiCallTrace, ApiCenterSummary, ApiCredential, ModelTaskName } from '@client/src/types/api';

const tabs = [
  { id: 'credentials', label: 'API 配置' },
  { id: 'calls', label: '调用记录' },
] as const;
type TabId = (typeof tabs)[number]['id'];

const usageOptions: Array<{ value: '' | ModelTaskName; label: string }> = [
  { value: '', label: '先保存，暂不使用' },
  { value: 'search_result_recommendation_reason', label: '搜索结果说明' },
  { value: 'asset_agent_chat', label: 'Piancton Agent' },
];

const taskLabels: Record<string, string> = {
  search_result_recommendation_reason: '搜索结果说明',
  asset_agent_chat: 'Piancton Agent',
};

interface CredentialDraft {
  label: string;
  baseUrl: string;
  modelName: string;
  apiKey: string;
  usage: '' | ModelTaskName;
}

const emptyDraft: CredentialDraft = {
  label: '',
  baseUrl: '',
  modelName: '',
  apiKey: '',
  usage: '',
};

export default function AdminApiCenter() {
  const [activeTab, setActiveTab] = useState<TabId>('credentials');
  const query = useQuery({ queryKey: ['api-center-summary'], queryFn: fetchApiCenterSummary });

  return (
    <div className="page-shell max-w-7xl">
      <PageHeader title="API 中心" />

      <div className="mt-6 inline-flex gap-1 rounded-xl border border-border bg-card p-1">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {query.isLoading ? (
        <p className="mt-7 text-sm text-muted-foreground">正在加载…</p>
      ) : query.isError ? (
        <p className="mt-7 text-sm text-destructive">{getApiError(query.error).message}</p>
      ) : query.data ? (
        <div className="mt-4">
          {activeTab === 'credentials' && <CredentialManager data={query.data} />}
          {activeTab === 'calls' && <CallHistory rows={query.data.recentCallTraces} />}
        </div>
      ) : null}
    </div>
  );
}

function CredentialManager({ data }: { data: ApiCenterSummary }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<CredentialDraft>(emptyDraft);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] });
  const create = useMutation({
    mutationFn: () => createApiCredential({
      label: draft.label.trim(),
      baseUrl: draft.baseUrl.trim(),
      modelName: draft.modelName.trim(),
      apiKey: draft.apiKey.trim(),
      taskScope: draft.usage ? [draft.usage] : [],
      status: 'active',
      timeoutSeconds: 60,
      temperature: 0.2,
      temperatureEnabled: true,
      autoAssignEnabled: Boolean(draft.usage),
      priority: 100,
    }),
    onSuccess: async () => {
      setDraft(emptyDraft);
      await refresh();
      toast.success('API 已保存');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });
  const update = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'active' | 'disabled' }) => (
      updateApiCredential(id, { status })
    ),
    onSuccess: refresh,
    onError: (error) => toast.error(getApiError(error).message),
  });
  const remove = useMutation({
    mutationFn: deleteApiCredential,
    onSuccess: async () => {
      await refresh();
      toast.success('API 已删除');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });
  const test = useMutation({
    mutationFn: ({ id, task }: { id: string; task: ModelTaskName }) => testApiCredential(id, task),
    onSuccess: async (result) => {
      await refresh();
      if (result.status === 'ok') toast.success('连接正常');
      else toast.error(result.errorSummary || '连接失败');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate();
  };
  const canSubmit = Boolean(
    draft.label.trim() && draft.baseUrl.trim() && draft.modelName.trim() && draft.apiKey.trim(),
  );

  return (
    <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
      <section className="surface-card h-fit overflow-hidden">
        <SectionTitle title="添加 API" />
        <form className="grid gap-4 p-5" onSubmit={submit}>
          <Field label="名称">
            <Input value={draft.label} onChange={(event) => setDraft({ ...draft, label: event.target.value })} placeholder="例如：业务问答 API" />
          </Field>
          <Field label="API 地址">
            <Input value={draft.baseUrl} onChange={(event) => setDraft({ ...draft, baseUrl: event.target.value })} placeholder="https://example.com/v1" />
          </Field>
          <Field label="模型名称">
            <Input value={draft.modelName} onChange={(event) => setDraft({ ...draft, modelName: event.target.value })} placeholder="模型名称" />
          </Field>
          <Field label="密钥">
            <Input type="password" value={draft.apiKey} onChange={(event) => setDraft({ ...draft, apiKey: event.target.value })} placeholder="API Key" />
          </Field>
          <Field label="使用位置">
            <Select value={draft.usage} onChange={(event) => setDraft({ ...draft, usage: event.target.value as CredentialDraft['usage'] })}>
              {usageOptions.map((option) => <option key={option.value || 'unused'} value={option.value}>{option.label}</option>)}
            </Select>
          </Field>
          <Button disabled={!canSubmit || create.isPending} className="mt-1">
            {create.isPending ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
            {create.isPending ? '正在测试…' : '测试并保存'}
          </Button>
        </form>
      </section>

      <section className="surface-card overflow-hidden">
        <SectionTitle title={`已保存的 API（${data.credentials.length}）`} />
        {data.credentials.length ? data.credentials.map((credential) => (
          <CredentialRow
            key={credential.id}
            credential={credential}
            testing={test.isPending && test.variables?.id === credential.id}
            updating={update.isPending && update.variables?.id === credential.id}
            deleting={remove.isPending && remove.variables === credential.id}
            onTest={() => test.mutate({
              id: credential.id,
              task: supportedTaskFor(credential),
            })}
            onToggle={() => update.mutate({
              id: credential.id,
              status: credential.status === 'active' ? 'disabled' : 'active',
            })}
            onDelete={() => {
              if (window.confirm(`删除「${credential.label}」？`)) remove.mutate(credential.id);
            }}
          />
        )) : (
          <div className="grid min-h-40 place-items-center text-sm text-muted-foreground">暂无 API</div>
        )}
      </section>
    </div>
  );
}

function CredentialRow({
  credential,
  testing,
  updating,
  deleting,
  onTest,
  onToggle,
  onDelete,
}: {
  credential: ApiCredential;
  testing: boolean;
  updating: boolean;
  deleting: boolean;
  onTest: () => void;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const usage = credential.taskScope
    .filter((task) => taskLabels[task])
    .map((task) => taskLabels[task])
    .join('、') || '暂未使用';
  return (
    <div className="border-b border-border/70 px-5 py-4 last:border-0">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-secondary"><KeyRound className="size-4" /></span>
            <h3 className="font-semibold">{credential.label}</h3>
            <Badge variant={credential.status === 'active' ? 'secondary' : 'outline'}>
              {credential.status === 'active' ? '启用' : '停用'}
            </Badge>
          </div>
          <p className="mt-3 text-sm font-medium">{credential.modelName}</p>
          <p className="mt-1 break-all text-xs text-muted-foreground">{credential.baseUrl}</p>
          <p className="mt-1 text-xs text-muted-foreground">{credential.apiKeyPreview} · {usage}</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled={testing} onClick={onTest}>
            {testing ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}测试
          </Button>
          <Button variant="outline" size="sm" disabled={updating} onClick={onToggle}>
            <Power className="size-4" />{credential.status === 'active' ? '停用' : '启用'}
          </Button>
          <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" disabled={deleting} onClick={onDelete}>
            <Trash2 className="size-4" />删除
          </Button>
        </div>
      </div>
    </div>
  );
}

function CallHistory({ rows }: { rows: ApiCallTrace[] }) {
  return (
    <section className="surface-card overflow-hidden">
      <SectionTitle title="最近调用" />
      {rows.length ? rows.slice(0, 100).map((row) => (
        <div
          key={row.id}
          className="grid gap-2 border-b border-border/70 px-5 py-4 text-sm last:border-0 md:grid-cols-[170px_minmax(180px,1fr)_minmax(180px,1fr)_100px_100px]"
        >
          <time className="text-xs text-muted-foreground">{new Date(row.createdAt).toLocaleString('zh-CN')}</time>
          <span>{taskLabels[row.task] || '其它用途'}</span>
          <span className="min-w-0 truncate text-muted-foreground">{row.credentialLabel || row.model || row.provider}</span>
          <Badge variant={row.status === 'ok' ? 'secondary' : 'outline'} className="h-fit w-fit">
            {row.status === 'ok' ? '成功' : row.status === 'timed_out' ? '超时' : '失败'}
          </Badge>
          <span className="text-xs text-muted-foreground">{row.durationMs} ms</span>
        </div>
      )) : <div className="grid min-h-40 place-items-center text-sm text-muted-foreground">暂无调用记录</div>}
    </section>
  );
}

function supportedTaskFor(credential: ApiCredential): ModelTaskName {
  const task = credential.taskScope.find((item) => item in taskLabels);
  return (task as ModelTaskName | undefined) ?? 'search_result_recommendation_reason';
}

function SectionTitle({ title }: { title: string }) {
  return <h2 className="border-b border-border bg-secondary/30 px-5 py-3 text-sm font-semibold">{title}</h2>;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1.5">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}
