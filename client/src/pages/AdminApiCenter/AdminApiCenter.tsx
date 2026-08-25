import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  ChevronDown,
  KeyRound,
  ListTree,
  RadioTower,
  Route,
} from 'lucide-react';

import {
  createApiCredential,
  fetchApiCenterSummary,
  runApiHealthChecks,
  testApiCredential,
  updateApiCredential,
  updateRoutingSlot,
} from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@client/src/components/ui/popover';
import { Select } from '@client/src/components/ui/select';
import type {
  ApiCenterSummary,
  ApiCredential,
  ApiCredentialCreate,
  ModelTaskName,
  RoutingSlotUpdate,
} from '@client/src/types/api';

const tabs = [
  { id: 'health', label: '健康度监测', icon: Activity },
  { id: 'keys', label: 'API 管理', icon: KeyRound },
  { id: 'routing', label: '调度配置', icon: Route },
  { id: 'traces', label: '调用链路日志', icon: ListTree },
] as const;

type TabId = (typeof tabs)[number]['id'];

const taskLabels: Record<string, string> = {
  search_system_routing: '第一层：体系路由',
  search_intent_understanding: '第二层：卖点识别',
  search_proof_point_understanding: '第三层：证明点识别',
  search_candidate_review: '第四层：候选图片复核',
  search_result_recommendation_reason: '搜索结果：动态推荐理由',
  search_embedding_recall: '搜索增强：Embedding 召回',
  search_reranker: '搜索增强：Reranker 重排',
  search_index: '搜索索引：Meilisearch',
  image_content_analysis: '上传主图：图片语义分析',
  asset_search_phrase_generation: '上传前：素材话术生成',
  copy_selling_point_matching: '兼容接口：文案卖点匹配',
  asset_agent_chat: '素材库 Agent：业务解释',
};

const healthCheckTaskLabels: Record<string, string> = {
  search_system_routing: taskLabels.search_system_routing,
  search_intent_understanding: taskLabels.search_intent_understanding,
  search_proof_point_understanding: taskLabels.search_proof_point_understanding,
  search_candidate_review: taskLabels.search_candidate_review,
  search_result_recommendation_reason: taskLabels.search_result_recommendation_reason,
  image_content_analysis: taskLabels.image_content_analysis,
  asset_search_phrase_generation: taskLabels.asset_search_phrase_generation,
  copy_selling_point_matching: taskLabels.copy_selling_point_matching,
  asset_agent_chat: taskLabels.asset_agent_chat,
};

const searchableTasks = [
  'search_system_routing',
  'search_intent_understanding',
  'search_proof_point_understanding',
  'search_candidate_review',
] as const satisfies readonly ModelTaskName[];

const statusClass: Record<string, string> = {
  active: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  ok: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  disabled: 'border-slate-200 bg-slate-50 text-slate-600',
  cooling: 'border-amber-200 bg-amber-50 text-amber-700',
  invalid: 'border-red-200 bg-red-50 text-red-700',
  failed: 'border-red-200 bg-red-50 text-red-700',
  timed_out: 'border-red-200 bg-red-50 text-red-700',
  idle: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  busy: 'border-slate-200 bg-slate-50 text-slate-700',
  saturated: 'border-amber-200 bg-amber-50 text-amber-700',
  degraded: 'border-red-200 bg-red-50 text-red-700',
};

const statusLabel: Record<string, string> = {
  ok: 'OK',
  failed: '失败',
  timed_out: '超时',
  skipped: '未配置/跳过',
  unknown: '未知',
};

const initialCredentialForm: ApiCredentialCreate = {
  label: '',
  providerType: 'openai_compatible',
  baseUrl: '',
  modelName: '',
  apiKey: '',
  taskScope: [...searchableTasks],
  status: 'active',
  priority: 100,
  timeoutSeconds: 20,
  temperature: 0.2,
  autoAssignEnabled: true,
};

const HEALTH_SCHEDULE_STORAGE_KEY = 'piancton.apiCenter.healthSchedule.v1';

interface HealthScheduleSettings {
  enabled: boolean;
  intervalHours: number;
  nextRunAt: number;
}

export default function AdminApiCenter() {
  const [activeTab, setActiveTab] = useState<TabId>('health');
  const query = useQuery({
    queryKey: ['api-center-summary'],
    queryFn: fetchApiCenterSummary,
  });
  const data = query.data;

  return (
    <div className="page-shell">
      <PageHeader
        eyebrow="API Center"
        title="API 中心"
        description="统一维护 API、健康检测、自动调度和真实调用链路。"
      />

      <div className="mt-7 flex flex-wrap gap-1 rounded-xl border border-border/80 bg-card p-1.5 shadow-sm">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <Button
              key={tab.id}
              variant={activeTab === tab.id ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon className="size-4" />
              {tab.label}
            </Button>
          );
        })}
      </div>

      {query.isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">正在加载 API 中心...</p>
      ) : query.isError ? (
        <p className="mt-6 text-sm text-destructive">{getApiError(query.error).message}</p>
      ) : data ? (
        <div className="mt-7 space-y-6">
          <Overview data={data} />
          {activeTab === 'health' && <HealthChecks data={data} />}
          {activeTab === 'keys' && <ApiKeys data={data} />}
          {activeTab === 'routing' && <RoutingSlots data={data} />}
          {activeTab === 'traces' && <CallTraces data={data} />}
        </div>
      ) : null}
    </div>
  );
}

function Overview({ data }: { data: ApiCenterSummary }) {
  const currentConcurrency = data.credentials.reduce(
    (total, item) => total + item.currentConcurrency,
    0,
  );
  const maxConcurrency = data.credentials.reduce(
    (total, item) => total + item.maxConcurrency,
    0,
  );
  const items = [
    ['API 总数', data.overview.credentialCount],
    ['启用 API', data.overview.activeCredentialCount],
    ['健康 API', data.overview.healthyCredentialCount],
    ['异常 API', data.overview.degradedCredentialCount],
    ['当前占用', `${currentConcurrency}/${maxConcurrency}`],
    ['已配槽位', data.overview.configuredSlotCount],
    ['24h 调用', data.overview.recentCallCount],
    ['24h 失败', data.overview.recentFailureCount],
    ['P95(ms)', data.overview.p95LatencyMs],
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {items.map(([label, value]) => (
        <div key={label} className="surface-card p-4">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">{label}</span>
            <RadioTower className="size-4 text-primary" />
          </div>
          <div className="mt-2 text-2xl font-semibold text-foreground">{value}</div>
        </div>
      ))}
    </div>
  );
}

function ApiKeys({ data }: { data: ApiCenterSummary }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ApiCredentialCreate>(initialCredentialForm);
  const createMutation = useMutation({
    mutationFn: createApiCredential,
    onSuccess: () => {
      setForm(initialCredentialForm);
      queryClient.invalidateQueries({ queryKey: ['api-center-summary'] });
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'active' | 'disabled' }) =>
      updateApiCredential(id, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    createMutation.mutate(form);
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
      <section className="surface-card overflow-hidden">
        <SectionHeader
          title="新增 API"
          description="保存后只显示掩码；开启自动分配后，系统会按健康数据自动选择可用 API。"
        />
        <form onSubmit={submit} className="grid gap-3 p-4">
          <LabeledInput
            label="API 别名"
            hint="例如 老张A、OpenAI备用、素材Agent"
            value={form.label}
            onChange={(value) => setForm({ ...form, label: value })}
          />
          <LabeledInput
            label="API 地址"
            hint="例如 https://xxx/v1"
            value={form.baseUrl}
            onChange={(value) => setForm({ ...form, baseUrl: value })}
          />
          <LabeledInput
            label="模型"
            hint="例如 gpt-5.5 / kimi-k2 / deepseek"
            value={form.modelName}
            onChange={(value) => setForm({ ...form, modelName: value })}
          />
          <LabeledInput
            label="密钥"
            hint="只保存，不回显完整值"
            type="password"
            value={form.apiKey}
            onChange={(value) => setForm({ ...form, apiKey: value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <label className="grid gap-1.5 text-sm">
              <span className="text-xs font-medium text-muted-foreground">超时秒数</span>
              <Input
                type="number"
                min={1}
                value={form.timeoutSeconds}
                onChange={(event) => setForm({ ...form, timeoutSeconds: Number(event.target.value) })}
              />
              <span className="text-[11px] leading-4 text-muted-foreground">
                单个 API 最多等待多久；超时或失败后，会在任务总预算内尝试下一个可用 API。
              </span>
            </label>
            <label className="grid gap-1.5 text-sm">
              <span className="text-xs font-medium text-muted-foreground">输出稳定度</span>
              <Input
                type="number"
                step="0.1"
                value={form.temperature}
                onChange={(event) => setForm({ ...form, temperature: Number(event.target.value) })}
              />
              <span className="text-[11px] leading-4 text-muted-foreground">
                也叫 temperature。0.2 更稳定，适合搜索判断；数值越高，回答越发散。
              </span>
            </label>
          </div>
          <div className="rounded-xl border border-border bg-secondary/60 px-3 py-2 text-xs leading-5 text-muted-foreground">
            并发容量不需要人工填写。系统会通过真实调用和容量压测估算安全容量，
            到上限后智能调度会优先换其他健康 API。
          </div>
          <label className="flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={form.autoAssignEnabled}
              onChange={(event) => setForm({ ...form, autoAssignEnabled: event.target.checked })}
            />
            <span>加入自动调度池</span>
          </label>
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? '保存中...' : '保存 API'}
          </Button>
          {createMutation.isError && (
            <p className="text-sm text-destructive">{getApiError(createMutation.error).message}</p>
          )}
        </form>
      </section>

      <section className="surface-card overflow-hidden">
        <SectionHeader
          title="API 列表"
          description="这里管理所有可用 API。完整密钥不会回显。"
        />
        <div className="divide-y divide-border">
          {data.credentials.length ? data.credentials.map((item) => (
            <div key={item.id} className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[1fr_auto]">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-foreground">{displayCredentialLabel(item)}</span>
                  <Badge variant="outline" className={statusClass[item.status] ?? ''}>{item.status}</Badge>
                  <Badge variant="outline" className={statusClass[item.capacityStatus] ?? ''}>
                    {capacityLabel(item.capacityStatus)}
                  </Badge>
                  {item.lastStatus && (
                    <Badge variant="outline" className={statusClass[item.lastStatus] ?? ''}>
                      最近 {item.lastStatus}
                    </Badge>
                  )}
                </div>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {item.modelName} · {item.apiKeyPreview}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  占用 {item.currentConcurrency}/{item.maxConcurrency} · 系统估算可用 {item.availableConcurrency}
                  · 24h 调用 {item.recentCallCount} · 失败率 {formatPercent(item.recentFailureRate)}
                  · 平均耗时 {item.recentAverageLatencyMs || item.lastLatencyMs || 0}ms
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  超时 {item.timeoutSeconds}s · 输出稳定度 {item.temperature} · 优先级 P{item.priority}
                  {item.autoAssignEnabled ? ' · 自动分配' : ' · 不参与自动分配'}
                  {item.lastLatencyMs ? ` · 最近耗时 ${item.lastLatencyMs}ms` : ''}
                  {item.lastError ? ` · ${item.lastError}` : ''}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateMutation.mutate({
                    id: item.id,
                    status: item.status === 'active' ? 'disabled' : 'active',
                  })}
                >
                  {item.status === 'active' ? '停用' : '启用'}
                </Button>
              </div>
            </div>
          )) : (
            <Empty text="还没有 API。先在左侧添加一个，再做健康测试。" />
          )}
        </div>
      </section>
    </div>
  );
}

function RoutingSlots({ data }: { data: ApiCenterSummary }) {
  const queryClient = useQueryClient();
  const [drafts, setDrafts] = useState<Record<string, RoutingSlotUpdate>>({});
  const credentialOptions = data.credentials;
  const saveMutation = useMutation({
    mutationFn: ({ task, payload }: { task: string; payload: RoutingSlotUpdate }) =>
      updateRoutingSlot(task, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });

  useEffect(() => {
    setDrafts((current) => {
      const next = { ...current };
      for (const slot of data.routingSlots) {
        if (next[slot.task]) continue;
        next[slot.task] = {
          primaryCredentialId: slot.primaryCredentialId ?? '',
          backupCredentialIds: slot.backupCredentialIds,
          timeoutSeconds: slot.timeoutSeconds,
          hedgingDelayMs: slot.hedgingDelayMs,
          maxParallel: slot.maxParallel,
          autoSelectEnabled: slot.autoSelectEnabled,
        };
      }
      return next;
    });
  }, [data.routingSlots]);

  const setDraft = (task: string, patch: RoutingSlotUpdate) => {
    setDrafts((current) => ({ ...current, [task]: { ...current[task], ...patch } }));
  };

  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader
        title="智能调度配置"
        description="开启自动调度时，每次调用都会综合健康、占用、并发上限、成功率、失败率和耗时选择 API；关闭后才按人工指定执行。"
      />
      <div className="border-b border-border bg-secondary/55 px-4 py-3 text-sm text-muted-foreground">
        超时秒数表示单个 API 最多等待多久；如果超时、失败或当前 API 满载，系统会在该任务剩余时间内尝试下一个健康 API。
      </div>
      <div className="divide-y divide-border">
        {data.routingSlots.map((slot) => {
          const draft = drafts[slot.task] ?? {};
          const autoEnabled = draft.autoSelectEnabled ?? slot.autoSelectEnabled;
          return (
            <div key={slot.task} className="api-routing-row text-sm">
              <div className="api-routing-copy min-w-0">
                <div className="font-medium text-foreground">{slot.label}</div>
                <div className="mt-1 text-xs text-muted-foreground">{slot.task}</div>
              </div>
              <div className="api-routing-panel">
                <button
                  type="button"
                  className="pc-switch"
                  data-checked={autoEnabled}
                  onClick={() => setDraft(slot.task, { autoSelectEnabled: !autoEnabled })}
                  aria-pressed={autoEnabled}
                >
                  <span className="pc-switch-track" />
                  <span>{autoEnabled ? '自动调度' : '人工指定'}</span>
                </button>
                <div className="api-routing-field">
                  <span className="api-routing-field-label">主 API</span>
                  <Select
                    value={draft.primaryCredentialId ?? ''}
                    onChange={(event) => setDraft(slot.task, { primaryCredentialId: event.target.value })}
                    disabled={autoEnabled}
                    className="bg-white/80"
                  >
                    <option value="">自动选择，不固定 API</option>
                    {credentialOptions.map((item) => (
                      <option key={item.id} value={item.id}>{displayCredentialLabel(item)}</option>
                    ))}
                  </Select>
                </div>
                <BackupPicker
                  credentials={credentialOptions}
                  selected={draft.backupCredentialIds ?? []}
                  onChange={(backupCredentialIds) => setDraft(slot.task, { backupCredentialIds })}
                  disabled={autoEnabled}
                />
                <div className="api-routing-actions">
                  <label className="api-routing-field">
                    <span className="api-routing-field-label">超时</span>
                    <Input
                      className="bg-white/80"
                      type="number"
                      min={1}
                      value={draft.timeoutSeconds ?? slot.timeoutSeconds}
                      onChange={(event) => setDraft(slot.task, { timeoutSeconds: Number(event.target.value) })}
                    />
                  </label>
                  <Button
                    size="sm"
                    disabled={saveMutation.isPending}
                    onClick={() => saveMutation.mutate({ task: slot.task, payload: draft })}
                  >
                    保存
                  </Button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function BackupPicker({
  credentials,
  selected,
  onChange,
  disabled,
}: {
  credentials: ApiCredential[];
  selected: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState('');
  const selectedCredentials = credentials.filter((item) => selected.includes(item.id));
  const filteredCredentials = credentials.filter((item) => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return true;
    return `${item.label} ${item.modelName}`.toLowerCase().includes(keyword);
  });
  const summary = disabled
    ? '自动调度时由系统选择'
    : selectedCredentials.length
      ? `已选 ${selectedCredentials.length} 个备用 API`
      : '未选择备用 API';

  const toggleCredential = (credentialId: string) => {
    onChange(
      selected.includes(credentialId)
        ? selected.filter((id) => id !== credentialId)
        : [...selected, credentialId],
    );
  };

  return (
    <div className={`api-routing-field api-backup-picker ${disabled ? 'is-disabled' : ''}`}>
      <div className="api-routing-field-label">
        备用池{disabled ? '（自动调度时由系统选择）' : ''}
      </div>
      <Popover>
        <PopoverTrigger asChild>
          <button
            type="button"
            className="api-backup-trigger"
            disabled={disabled || !credentials.length}
          >
            <span>{summary}</span>
            <ChevronDown className="size-4 text-muted-foreground" />
          </button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-[22rem] rounded-xl p-2">
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索 API"
            className="mb-2"
          />
          <div className="api-backup-menu compact-scrollbar">
            {filteredCredentials.length ? filteredCredentials.map((item) => {
              const checked = selected.includes(item.id);
              return (
                <label key={item.id} className="api-backup-option">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleCredential(item.id)}
                  />
                  <span className="min-w-0">
                    <span className="block truncate text-sm text-foreground">{displayCredentialLabel(item)}</span>
                    <span className="block truncate text-xs text-muted-foreground">{item.modelName}</span>
                  </span>
                </label>
              );
            }) : <span className="block px-2 py-3 text-sm text-muted-foreground">暂无匹配 API</span>}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}

function HealthChecks({ data }: { data: ApiCenterSummary }) {
  const queryClient = useQueryClient();
  const [credentialId, setCredentialId] = useState(data.credentials[0]?.id ?? '');
  const [task, setTask] = useState<ModelTaskName>('search_system_routing');
  const [schedule, setSchedule] = useState<HealthScheduleSettings>(() => loadHealthSchedule());
  const runAllMutation = useMutation({
    mutationFn: () => runApiHealthChecks({ includeDisabled: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-center-summary'] });
      setSchedule((current) => saveHealthSchedule(nextHealthSchedule(current)));
    },
  });
  const testMutation = useMutation({
    mutationFn: () => testApiCredential(credentialId, task),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });

  useEffect(() => {
    if (!credentialId && data.credentials[0]?.id) {
      setCredentialId(data.credentials[0].id);
    }
  }, [credentialId, data.credentials]);

  useEffect(() => {
    if (!schedule.enabled || runAllMutation.isPending) return;
    if (Date.now() < schedule.nextRunAt) return;
    runAllMutation.mutate();
  }, [runAllMutation, schedule.enabled, schedule.nextRunAt]);

  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader
        title="健康度监测"
        description="这里分开看三件事：真实调用自动回写、一键巡检、定时巡检。"
      />
      {(runAllMutation.isSuccess || testMutation.isSuccess) && (
        <div className="border-b border-border bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {runAllMutation.data
            ? `巡检完成：共 ${runAllMutation.data.checkedCount} 个，健康 ${runAllMutation.data.okCount} 个，异常 ${runAllMutation.data.failedCount} 个。`
            : '单个 API 测试完成。'}
        </div>
      )}
      {(runAllMutation.isError || testMutation.isError) && (
        <div className="border-b border-border bg-red-50 px-4 py-3 text-sm text-red-700">
          {getApiError(runAllMutation.error ?? testMutation.error).message}
        </div>
      )}
      <div className="grid gap-3 border-b border-border bg-muted/20 p-4 xl:grid-cols-3">
        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="text-sm font-semibold text-foreground">自动监测</h3>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            每次真实模型调用结束后，系统会自动写回成功/失败、耗时和错误摘要。
            这部分不需要手动开启，也是调度算法最重要的数据。
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="text-sm font-semibold text-foreground">一键巡检</h3>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            管理员主动点一次，系统会用最小 JSON 探针检测 API 是否能跑通。
          </p>
          <div className="mt-3 grid gap-2">
            <Button
              size="sm"
              disabled={!data.credentials.length || runAllMutation.isPending}
              onClick={() => runAllMutation.mutate()}
            >
              {runAllMutation.isPending ? '巡检中...' : '一键巡检全部 API'}
            </Button>
            <div className="grid gap-2">
              <Select
                value={credentialId}
                onChange={(event) => setCredentialId(event.target.value)}
              >
                {data.credentials.map((item) => (
                  <option key={item.id} value={item.id}>
                    {displayCredentialLabel(item)} · {item.modelName}
                  </option>
                ))}
              </Select>
              <Select
                value={task}
                onChange={(event) => setTask(event.target.value as ModelTaskName)}
              >
                {Object.entries(healthCheckTaskLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </Select>
              <Button
                variant="outline"
                size="sm"
                disabled={!credentialId || testMutation.isPending}
                onClick={() => testMutation.mutate()}
              >
                {testMutation.isPending ? '测试中...' : '测试单个 API'}
              </Button>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="text-sm font-semibold text-foreground">定时巡检</h3>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            当前测试版会在打开 API 中心时检查是否到期；到期后自动巡检全部 API。
            服务器正式部署后，可把同一个巡检接口接入 cron 或任务队列。
          </p>
          <div className="mt-3 grid gap-2 text-sm">
            <label className="flex items-center gap-2 rounded-xl border border-border px-3 py-2">
              <input
                type="checkbox"
                checked={schedule.enabled}
                onChange={(event) => {
                  setSchedule(saveHealthSchedule({
                    ...schedule,
                    enabled: event.target.checked,
                    nextRunAt: Date.now() + schedule.intervalHours * 60 * 60 * 1000,
                  }));
                }}
              />
              <span>开启定时巡检</span>
            </label>
            <label className="grid gap-1 text-xs text-muted-foreground">
              巡检间隔（小时）
              <Input
                type="number"
                min={1}
                max={168}
                value={schedule.intervalHours}
                onChange={(event) => {
                  const intervalHours = Math.max(1, Number(event.target.value) || 24);
                  setSchedule(saveHealthSchedule({
                    ...schedule,
                    intervalHours,
                    nextRunAt: Date.now() + intervalHours * 60 * 60 * 1000,
                  }));
                }}
              />
            </label>
            <p className="text-xs text-muted-foreground">
              下次巡检：{schedule.enabled ? new Date(schedule.nextRunAt).toLocaleString('zh-CN') : '未开启'}
            </p>
          </div>
        </div>
      </div>
      <div className="divide-y divide-border">
        {data.recentHealthChecks.length ? data.recentHealthChecks.map((item) => (
          <div key={item.id} className="grid gap-3 px-4 py-3 text-sm md:grid-cols-[180px_1fr_100px_100px_180px]">
            <span className="font-medium text-foreground">
              {displayCredentialName(item.credentialLabel ?? item.credentialId)}
            </span>
            <span className="text-muted-foreground">{taskLabels[item.task] ?? item.task}</span>
            <Badge variant="outline" className={`w-fit ${statusClass[item.status] ?? ''}`}>
              {statusLabel[item.status] ?? item.status}
            </Badge>
            <span>{item.durationMs}ms</span>
            <span className="text-xs text-muted-foreground">{new Date(item.checkedAt).toLocaleString('zh-CN')}</span>
            {item.errorSummary && <p className="md:col-span-5 text-xs text-destructive">{item.errorSummary}</p>}
          </div>
        )) : (
          <Empty text="暂无健康测试记录。" />
        )}
      </div>
    </section>
  );
}

function CallTraces({ data }: { data: ApiCenterSummary }) {
  const rows = useMemo(() => data.recentCallTraces.slice(0, 80), [data.recentCallTraces]);
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader
        title="全项目 API 调用链路"
        description="这里统一显示上传分析、话术生成、搜索、素材库 Agent、文案匹配和健康检查等模型/API 调用结果；不包含完整密钥、Prompt、图片或聊天正文。"
      />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="border-b border-border bg-muted/40 text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">时间</th>
              <th className="px-4 py-3 font-medium">层级</th>
              <th className="px-4 py-3 font-medium">Provider / 模型</th>
              <th className="px-4 py-3 font-medium">API</th>
              <th className="px-4 py-3 font-medium">状态</th>
              <th className="px-4 py-3 font-medium">耗时</th>
              <th className="px-4 py-3 font-medium">错误摘要</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.length ? rows.map((item) => (
              <tr key={item.id}>
                <td className="px-4 py-3 text-xs text-muted-foreground">{new Date(item.createdAt).toLocaleString('zh-CN')}</td>
                <td className="px-4 py-3">
                  <div className="font-medium text-foreground">{item.layerName}</div>
                  <div className="text-xs text-muted-foreground">{item.task}</div>
                </td>
                <td className="px-4 py-3">{item.provider} / {item.model}</td>
                <td className="px-4 py-3">
                  {displayCredentialName(item.credentialLabel ?? '环境配置或未登记')}
                </td>
                <td className="px-4 py-3">
                  <Badge variant="outline" className={statusClass[item.status] ?? ''}>
                    {statusLabel[item.status] ?? item.status}
                  </Badge>
                </td>
                <td className="px-4 py-3">{item.durationMs}ms</td>
                <td className="px-4 py-3 text-xs text-muted-foreground">{item.errorSummary || '—'}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={7}><Empty text="暂无 API 调用记录。项目中的任一模型/API 调用完成后都会出现在这里。" /></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SectionHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="border-b border-border px-4 py-3">
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

function displayCredentialLabel(item: ApiCredential): string {
  return displayCredentialName(item.label);
}

function displayCredentialName(label: string): string {
  return label
    .replace('环境导入 · ', '')
    .replace(' Key', ' API');
}

function capacityLabel(status: string): string {
  const labels: Record<string, string> = {
    idle: '空闲',
    busy: '占用中',
    saturated: '已满载',
    degraded: '需关注',
  };
  return labels[status] ?? status;
}

function formatPercent(value: number): string {
  return `${Math.round((value || 0) * 100)}%`;
}

function loadHealthSchedule(): HealthScheduleSettings {
  const fallback: HealthScheduleSettings = {
    enabled: false,
    intervalHours: 24,
    nextRunAt: Date.now() + 24 * 60 * 60 * 1000,
  };
  try {
    const raw = window.localStorage.getItem(HEALTH_SCHEDULE_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    const intervalHours = Math.max(1, Number(parsed?.intervalHours || 24));
    return {
      enabled: Boolean(parsed?.enabled),
      intervalHours,
      nextRunAt: Number(parsed?.nextRunAt || Date.now() + intervalHours * 60 * 60 * 1000),
    };
  } catch {
    return fallback;
  }
}

function saveHealthSchedule(value: HealthScheduleSettings): HealthScheduleSettings {
  try {
    window.localStorage.setItem(HEALTH_SCHEDULE_STORAGE_KEY, JSON.stringify(value));
  } catch {
    // localStorage 不可用时，仅保留当前页面内的设置。
  }
  return value;
}

function nextHealthSchedule(value: HealthScheduleSettings): HealthScheduleSettings {
  return {
    ...value,
    nextRunAt: Date.now() + value.intervalHours * 60 * 60 * 1000,
  };
}

function LabeledInput({
  label,
  hint,
  value,
  onChange,
  type = 'text',
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="grid gap-1.5 text-sm">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <Input
        placeholder={hint}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="px-4 py-5 text-sm text-muted-foreground">{text}</p>;
}
