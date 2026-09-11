import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  Ban,
  ChevronDown,
  Database,
  KeyRound,
  ListTree,
  PowerOff,
  RadioTower,
  Route,
  Save,
  Sparkles,
  Trash2,
} from 'lucide-react';

import {
  createApiCredential,
  deleteApiCredential,
  diagnoseExternalSearchChain,
  disableApiProviderGroup,
  fetchApiCallTraces,
  fetchApiCenterSummary,
  probeApiCredentialTemperature,
  runApiCenterMaintenance,
  runApiHealthChecks,
  testExternalKnowledgeService,
  testExternalVectorDatabase,
  testApiCredential,
  updateApiCredential,
  updateExternalKnowledgeService,
  updateExternalVectorDatabase,
  updateRoutingSlot,
} from '@client/src/api/admin';
import {
  NEW_API_PROBE_LIMIT_SECONDS,
  recommendedApiCallLimitSeconds,
} from '@client/src/api/apiCenterWaitPolicy';
import { getApiError } from '@client/src/api/client';
import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@client/src/components/ui/popover';
import { Select } from '@client/src/components/ui/select';
import type {
  ApiCallTrace,
  ApiCenterSummary,
  ApiCredential,
  ApiCredentialCreate,
  ApiCredentialUpdate,
  ApiExternalConnectionTestResult,
  ApiExternalKnowledgeServiceUpdate,
  ApiSearchChainDiagnosticResult,
  ApiExternalVectorDatabaseUpdate,
  ApiTemperatureTuneResult,
  ModelTaskName,
  RoutingSlotUpdate,
} from '@client/src/types/api';

const tabs = [
  { id: 'health', label: '健康度监测', icon: Activity },
  { id: 'keys', label: 'API 管理', icon: KeyRound },
  { id: 'external', label: '知识与数据库', icon: Database },
  { id: 'routing', label: '模型位置', icon: Route },
  { id: 'traces', label: '调用链路日志', icon: ListTree },
] as const;

type TabId = (typeof tabs)[number]['id'];

const currentTaskLabels: Record<string, string> = {
  search_result_recommendation_reason: '搜索结果：命中卖点解释',
  asset_agent_chat: 'Piancton Agent：通用业务问答',
};

const retiredTaskLabels: Record<string, string> = {
  search_system_routing: '已退役：旧体系路由',
  search_intent_understanding: '已退役：旧卖点识别',
  search_proof_point_understanding: '已退役：旧证明点识别',
  search_candidate_review: '已退役：旧候选图片复核',
  search_embedding_recall: '搜索增强：Embedding 召回',
  search_reranker: '搜索增强：Reranker 重排',
  search_index: '搜索索引：Meilisearch',
  image_content_analysis: '已退役：上传主图语义分析',
  copy_selling_point_matching: '已退役：文案卖点匹配',
};

const taskLabels: Record<string, string> = {
  ...currentTaskLabels,
  ...retiredTaskLabels,
};

const routingSlotDescriptions: Record<string, string> = {
  search_result_recommendation_reason:
    '搜索结果顶部的黑色说明，只解释用户原话为什么命中这些卖点；不参与火山召回、排序或候选准入。',
  asset_agent_chat:
    '右侧 Piancton Agent 的通用业务问答位置，可回答图片、卖点、体系和销售话术；不写入业务事实。',
};

const statusClass: Record<string, string> = {
  active: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  ok: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  disabled: 'border-slate-200 bg-slate-50 text-slate-600',
  cooling: 'border-amber-200 bg-amber-50 text-amber-700',
  invalid: 'border-red-200 bg-red-50 text-red-700',
  failed: 'border-red-200 bg-red-50 text-red-700',
  timed_out: 'border-red-200 bg-red-50 text-red-700',
  skipped: 'border-slate-200 bg-slate-50 text-slate-600',
  idle: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  busy: 'border-slate-200 bg-slate-50 text-slate-700',
  saturated: 'border-amber-200 bg-amber-50 text-amber-700',
  watch: 'border-amber-200 bg-amber-50 text-amber-700',
  degraded: 'border-red-200 bg-red-50 text-red-700',
  unknown: 'border-slate-200 bg-slate-50 text-slate-600',
};

const statusLabel: Record<string, string> = {
  ok: 'OK',
  failed: '失败',
  degraded: '降级可用',
  timed_out: '超时',
  skipped: '未配置/跳过',
  unknown: '未知',
};

const errorCategoryLabel: Record<string, string> = {
  configuration: '配置',
  authentication: '鉴权',
  connectivity: '连接',
  capacity: '容量',
  rate_limit: '限流',
  upstream: '上游',
  timeout: '等待',
  compatibility: '兼容',
  response_contract: '响应契约',
  cancellation: '取消',
  scheduler: '调度',
  unknown: '未知',
};

const errorSeverityLabel: Record<string, string> = {
  info: '提示',
  warning: '观察',
  error: '处理',
  critical: '立即处理',
};

const errorSeverityClass: Record<string, string> = {
  info: 'border-slate-200 bg-slate-50 text-slate-600',
  warning: 'border-amber-200 bg-amber-50 text-amber-700',
  error: 'border-red-200 bg-red-50 text-red-700',
  critical: 'border-red-300 bg-red-100 text-red-800',
};

const initialCredentialForm: ApiCredentialCreate = {
  label: '',
  providerType: 'openai_compatible',
  baseUrl: '',
  modelName: '',
  apiKey: '',
  status: 'active',
  priority: 100,
  timeoutSeconds: 20,
  temperature: 0.2,
  temperatureEnabled: true,
  taskScope: ['search_result_recommendation_reason', 'asset_agent_chat'],
  autoAssignEnabled: true,
};

function credentialProbeSignature(form: ApiCredentialCreate): string {
  return JSON.stringify({
    baseUrl: form.baseUrl.trim(),
    modelName: form.modelName.trim(),
    apiKey: form.apiKey.trim(),
    temperature: form.temperature,
    temperatureEnabled: form.temperatureEnabled,
  });
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
        description="统一管理模型 API、卖点知识库和 VikingDB 向量库；搜索主判断走知识库，未命中时再由向量库做 top1 兜底，本地图库仍是最终事实源。"
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
          {activeTab === 'health' && (
            <HealthChecks data={data} onOpenTraces={() => setActiveTab('traces')} />
          )}
          {activeTab === 'keys' && <ApiKeys data={data} />}
          {activeTab === 'external' && <ExternalConnections data={data} />}
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
    ['已配位置', data.overview.configuredSlotCount],
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
  const [successfulProbeSignature, setSuccessfulProbeSignature] = useState<string | null>(null);
  const probeSignature = useMemo(() => credentialProbeSignature(form), [form]);
  const canProbe = Boolean(
    form.baseUrl.trim()
    && form.modelName.trim()
    && form.apiKey.trim()
  );
  const hasCurrentProbePassed = successfulProbeSignature === probeSignature;
  const createMutation = useMutation({
    mutationFn: createApiCredential,
    onSuccess: () => {
      setForm(initialCredentialForm);
      setSuccessfulProbeSignature(null);
      queryClient.invalidateQueries({ queryKey: ['api-center-summary'] });
    },
  });
  const probeMutation = useMutation({
    mutationFn: () => probeApiCredentialTemperature({
      baseUrl: form.baseUrl,
      modelName: form.modelName,
      apiKey: form.apiKey,
      task: 'search_result_recommendation_reason',
      temperature: form.temperature ?? 0.2,
      timeoutSeconds: NEW_API_PROBE_LIMIT_SECONDS,
    }),
    onSuccess: (result) => {
      if (result.status === 'ok' && result.selectedTemperatureEnabled != null) {
        const recommendedCallLimit = recommendedApiCallLimitSeconds(
          result.probes.map((probe) => probe.durationMs),
        );
        const nextForm = {
          ...form,
          timeoutSeconds: recommendedCallLimit,
          temperature: result.selectedTemperature ?? form.temperature ?? 0.2,
          temperatureEnabled: result.selectedTemperatureEnabled,
        };
        setForm(nextForm);
        setSuccessfulProbeSignature(credentialProbeSignature(nextForm));
      } else {
        setSuccessfulProbeSignature(null);
      }
    },
    onError: () => setSuccessfulProbeSignature(null),
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ApiCredentialUpdate }) =>
      updateApiCredential(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteApiCredential,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });
  const disableProviderGroupMutation = useMutation({
    mutationFn: disableApiProviderGroup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!hasCurrentProbePassed) return;
    createMutation.mutate(form);
  };

  return (
    <div className="grid gap-4">
      <ProviderGroups
        data={data}
        isDisabling={disableProviderGroupMutation.isPending}
        onDisableProviderGroup={(providerGroup) => {
          if (window.confirm(`确认停用 ${providerGroup} 下的全部 API？`)) {
            disableProviderGroupMutation.mutate(providerGroup);
          }
        }}
      />
      {disableProviderGroupMutation.isError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {getApiError(disableProviderGroupMutation.error).message}
        </div>
      )}
      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <section className="surface-card overflow-hidden">
          <SectionHeader
            title="新增 API"
            description="这里维护所有经过测试的可用模型。保存后会立即进入人工可选库存；是否参与自动调度由下方开关决定。"
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
            <div className="grid content-start gap-1.5 text-sm">
              <span className="text-xs font-medium text-muted-foreground">单次调用上限</span>
              <div className="flex h-10 items-center rounded-md border border-input bg-muted/40 px-3 text-sm text-foreground">
                {hasCurrentProbePassed ? `${form.timeoutSeconds} 秒` : '测试后自动设置'}
              </div>
              <span className="text-[11px] leading-4 text-muted-foreground">
                无需填写。系统会根据真实测试耗时自动留出安全余量。
              </span>
            </div>
            <label className="grid gap-1.5 text-sm">
              <span className="text-xs font-medium text-muted-foreground">输出稳定度</span>
              <Input
                type="number"
                step="0.1"
                value={form.temperature}
                disabled={!form.temperatureEnabled}
                onChange={(event) => setForm({ ...form, temperature: Number(event.target.value) })}
              />
              <span className="flex items-center gap-2 text-[11px] leading-4 text-muted-foreground">
                <input
                  type="checkbox"
                  checked={form.temperatureEnabled}
                  onChange={(event) => setForm({
                    ...form,
                    temperatureEnabled: event.target.checked,
                  })}
                />
                发送 temperature 参数
              </span>
              <span className="text-[11px] leading-4 text-muted-foreground">
                测试会自动匹配可用值；模型不接受该参数时会自动关闭发送。
              </span>
            </label>
          </div>
          <div className="rounded-xl border border-border bg-secondary/60 px-3 py-2 text-xs leading-5 text-muted-foreground">
            并发容量采用默认安全值。到上限后智能调度会优先换其他健康 API；
            后续接入容量探测后再自动写回。
          </div>
          <label className="flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={form.autoAssignEnabled}
              onChange={(event) => setForm({ ...form, autoAssignEnabled: event.target.checked })}
            />
            <span>允许进入自动候选池（关闭后仍可人工指定）</span>
          </label>
          <Button
            type="button"
            variant="outline"
            disabled={probeMutation.isPending || !canProbe}
            onClick={() => probeMutation.mutate()}
          >
            <Sparkles className="size-4" />
            {probeMutation.isPending ? '正在测试连接与参数...' : '测试 API 并自动设置'}
          </Button>
          {probeMutation.isSuccess && (
            <p className="text-sm text-emerald-700">
              {temperatureTuneMessage(probeMutation.data)}
              {probeMutation.data.status === 'ok'
                ? ` 单次调用上限已自动设置为 ${form.timeoutSeconds} 秒。`
                : ''}
            </p>
          )}
          {probeMutation.isError && (
            <p className="text-sm text-destructive">
              {getApiError(probeMutation.error).message}
            </p>
          )}
          {!hasCurrentProbePassed && canProbe && (
            <p className="text-xs text-muted-foreground">当前 API 需要先测试通过，再保存到 API 库存。</p>
          )}
          <Button type="submit" disabled={createMutation.isPending || !hasCurrentProbePassed}>
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
                <CapabilityBadges credential={item} />
                <p className="mt-1 text-xs text-muted-foreground">
                  占用 {item.currentConcurrency}/{item.maxConcurrency} · 当前可接 {item.availableConcurrency}
                  · 24h 调用 {item.recentCallCount} · 失败率 {formatPercent(item.recentFailureRate)}
                  · 平均耗时 {item.recentAverageLatencyMs || item.lastLatencyMs || 0}ms
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  单次调用上限 {item.timeoutSeconds}s · 输出稳定度 {item.temperatureEnabled ? item.temperature : '不发送 temperature'}
                  · 优先级 P{item.priority}
                  {item.autoAssignEnabled ? ' · 允许自动候选' : ' · 仅人工使用'}
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
                    payload: { status: item.status === 'active' ? 'disabled' : 'active' },
                  })}
                >
                  {item.status === 'active' ? '停用' : '启用'}
                </Button>
                <button
                  type="button"
                  className="pc-switch"
                  data-checked={item.autoAssignEnabled}
                  disabled={updateMutation.isPending}
                  onClick={() => updateMutation.mutate({
                    id: item.id,
                    payload: { autoAssignEnabled: !item.autoAssignEnabled },
                  })}
                  aria-pressed={item.autoAssignEnabled}
                  title={item.autoAssignEnabled ? '移出自动候选池' : '允许进入自动候选池'}
                >
                  <span className="pc-switch-track" />
                  <span>{item.autoAssignEnabled ? '允许自动候选' : '仅人工使用'}</span>
                </button>
                <Button
                  variant="outline"
                  size="icon"
                  aria-label={`删除 ${displayCredentialLabel(item)}`}
                  title="删除 API"
                  disabled={deleteMutation.isPending}
                  onClick={() => {
                    if (window.confirm(`确认删除 ${displayCredentialLabel(item)}？`)) {
                      deleteMutation.mutate(item.id);
                    }
                  }}
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
            </div>
            )) : (
              <Empty text="还没有 API。先在左侧添加一个，再做健康测试。" />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function ProviderGroups({
  data,
  isDisabling,
  onDisableProviderGroup,
}: {
  data: ApiCenterSummary;
  isDisabling: boolean;
  onDisableProviderGroup: (providerGroup: string) => void;
}) {
  if (!data.providerGroups.length) return null;
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader
        title="中转站概览"
        description="按 API 地址主机名聚合，帮助判断是不是某个站整体波动；系统只给建议，是否整站停用由管理员决定。"
      />
      <div className="divide-y divide-border">
        {data.providerGroups.map((group) => (
          <div
            key={group.providerGroup}
            className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[1fr_auto]"
          >
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-foreground">{group.providerGroup}</span>
                <Badge variant="outline" className={statusClass[group.status] ?? ''}>
                  {providerGroupStatusLabel(group.status)}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                API {group.credentialCount} 个 · 启用 {group.activeCredentialCount} 个
                · 自动候选 {group.autoAssignCredentialCount} 个 · 当前占用 {group.currentConcurrency}
                · 24h 调用 {group.recentCallCount} · 失败率 {formatPercent(group.recentFailureRate)}
                · 超时 {group.recentTimeoutCount}
              </p>
              {group.recommendation && (
                <p className="mt-1 text-xs text-muted-foreground">{group.recommendation}</p>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={isDisabling || group.activeCredentialCount === 0}
              onClick={() => onDisableProviderGroup(group.providerGroup)}
            >
              <PowerOff className="size-4" />
              停用此站
            </Button>
          </div>
        ))}
      </div>
    </section>
  );
}

function CapabilityBadges({ credential }: { credential: ApiCredential }) {
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {credential.capabilityProfile.map((capability) => (
        <Badge
          key={capability.capability}
          variant="outline"
          className={statusClass[capability.status] ?? ''}
          title={capabilityTooltip(capability)}
        >
          {capability.label} · {capabilityStatusLabel(capability.status)}
        </Badge>
      ))}
    </div>
  );
}

function ExternalConnections({ data }: { data: ApiCenterSummary }) {
  const queryClient = useQueryClient();
  const [knowledgeForm, setKnowledgeForm] = useState<ApiExternalKnowledgeServiceUpdate>({
    ...data.externalConnections.knowledgeService,
    apiKey: '',
  });
  const [vectorForm, setVectorForm] = useState<ApiExternalVectorDatabaseUpdate>({
    ...data.externalConnections.vectorDatabase,
    apiKey: '',
  });
  const [diagnosticQuery, setDiagnosticQuery] = useState('洋葱拍题精学习');
  const saveKnowledgeMutation = useMutation({
    mutationFn: updateExternalKnowledgeService,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });
  const saveVectorMutation = useMutation({
    mutationFn: updateExternalVectorDatabase,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });
  const testKnowledgeMutation = useMutation({
    mutationFn: () => testExternalKnowledgeService(),
  });
  const testVectorMutation = useMutation({
    mutationFn: () => testExternalVectorDatabase(),
  });
  const diagnoseMutation = useMutation({
    mutationFn: () => diagnoseExternalSearchChain(diagnosticQuery),
  });

  useEffect(() => {
    setKnowledgeForm((current) => ({
      ...data.externalConnections.knowledgeService,
      apiKey: current.apiKey ?? '',
    }));
    setVectorForm((current) => ({
      ...data.externalConnections.vectorDatabase,
      apiKey: current.apiKey ?? '',
    }));
  }, [data.externalConnections]);

  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader
        title="知识与数据库调度"
        description="这里决定搜索先问哪个知识库、失败后是否进入向量库兜底。页面保存后即写入 API Center，后端下一次搜索会优先读取这里的配置。"
      />
      <div className="border-b border-border bg-muted/20 p-4">
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-end">
            <div>
              <h3 className="text-base font-semibold text-foreground">完整搜索链路体检</h3>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                用同一句话依次检查：API Center 配置、知识库主判断、VikingDB 兜底、最终搜索是否真的产出卖点和图片结果。
              </p>
              <Input
                className="mt-3"
                value={diagnosticQuery}
                onChange={(event) => setDiagnosticQuery(event.target.value)}
                placeholder="输入一条测试搜索，例如：考前复习 / 洋葱拍题精学习"
              />
            </div>
            <Button
              disabled={diagnoseMutation.isPending}
              onClick={() => diagnoseMutation.mutate()}
            >
              <Sparkles className="size-4" />
              {diagnoseMutation.isPending ? '体检中...' : '一键体检完整链路'}
            </Button>
          </div>
          {diagnoseMutation.isError ? (
            <p className="mt-3 text-sm text-destructive">
              {getApiError(diagnoseMutation.error).message}
            </p>
          ) : null}
          {diagnoseMutation.data ? (
            <SearchChainDiagnosticPanel result={diagnoseMutation.data} />
          ) : null}
        </div>
      </div>
      <div className="grid gap-4 bg-muted/20 p-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-foreground">卖点知识库服务</h3>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                作为主判断：负责理解用户这句话属于哪个业务体系/核心卖点，并输出“结果、判断、定义”。
              </p>
            </div>
            <Badge
              variant="outline"
              className={knowledgeForm.enabled ? statusClass.ok : statusClass.disabled}
            >
              {knowledgeForm.enabled ? '主判断启用' : '已停用'}
            </Badge>
          </div>
          <div className="mt-4 grid gap-3">
            <SwitchField
              checked={Boolean(knowledgeForm.enabled)}
              label="启用为卖点主判断"
              onChange={(enabled) => setKnowledgeForm({ ...knowledgeForm, enabled })}
            />
            <LabeledInput
              label="服务地址"
              hint="https://api-knowledgebase..."
              value={knowledgeForm.baseUrl ?? ''}
              onChange={(baseUrl) => setKnowledgeForm({ ...knowledgeForm, baseUrl })}
            />
            <LabeledInput
              label="服务 ID"
              hint="kb-service-..."
              value={knowledgeForm.serviceResourceId ?? ''}
              onChange={(serviceResourceId) => (
                setKnowledgeForm({ ...knowledgeForm, serviceResourceId })
              )}
            />
            <LabeledInput
              label="API Key"
              hint={
                data.externalConnections.knowledgeService.apiKeyConfigured
                  ? '已配置，留空不修改'
                  : '未配置，请粘贴 key'
              }
              type="password"
              value={knowledgeForm.apiKey ?? ''}
              onChange={(apiKey) => setKnowledgeForm({ ...knowledgeForm, apiKey })}
            />
            <div className="grid gap-3 sm:grid-cols-3">
              <NumberField
                label="超时秒数"
                value={knowledgeForm.timeoutSeconds ?? 12}
                min={0.5}
                step={0.5}
                onChange={(timeoutSeconds) => setKnowledgeForm({ ...knowledgeForm, timeoutSeconds })}
              />
              <NumberField
                label="参考片段数"
                value={knowledgeForm.resultLimit ?? 6}
                min={1}
                max={20}
                step={1}
                onChange={(resultLimit) => setKnowledgeForm({ ...knowledgeForm, resultLimit })}
              />
              <NumberField
                label="最多卖点数"
                value={knowledgeForm.maxMatches ?? 4}
                min={1}
                max={6}
                step={1}
                onChange={(maxMatches) => setKnowledgeForm({ ...knowledgeForm, maxMatches })}
              />
            </div>
          </div>
          <ConnectionActions
            isSaving={saveKnowledgeMutation.isPending}
            isTesting={testKnowledgeMutation.isPending}
            onSave={() => saveKnowledgeMutation.mutate(knowledgeForm)}
            onTest={() => testKnowledgeMutation.mutate()}
          />
          <MutationMessage mutation={saveKnowledgeMutation} successText="卖点知识库配置已保存。" />
          <TestMessage mutation={testKnowledgeMutation} />
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-foreground">VikingDB V2 向量库</h3>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                作为兜底判断：知识库没识别出来时，只取 top1；分数低于阈值直接打回，避免乱推。
              </p>
            </div>
            <Badge
              variant="outline"
              className={vectorForm.fallbackEnabled ? statusClass.ok : statusClass.disabled}
            >
              {vectorForm.fallbackEnabled ? '兜底启用' : '兜底关闭'}
            </Badge>
          </div>
          <div className="mt-4 grid gap-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <SwitchField
                checked={Boolean(vectorForm.enabled)}
                label="允许向量库判断卖点"
                onChange={(enabled) => setVectorForm({ ...vectorForm, enabled })}
              />
              <SwitchField
                checked={Boolean(vectorForm.fallbackEnabled)}
                label="作为知识库兜底"
                onChange={(fallbackEnabled) => setVectorForm({ ...vectorForm, fallbackEnabled })}
              />
            </div>
            <LabeledInput
              label="服务地址"
              hint="https://api-vikingdb..."
              value={vectorForm.baseUrl ?? ''}
              onChange={(baseUrl) => setVectorForm({ ...vectorForm, baseUrl })}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <LabeledInput
                label="Collection"
                hint="piancton_search_knowledge_v2..."
                value={vectorForm.collectionName ?? ''}
                onChange={(collectionName) => setVectorForm({ ...vectorForm, collectionName })}
              />
              <LabeledInput
                label="Index"
                hint="piancton_knowledge_v2_idx"
                value={vectorForm.indexName ?? ''}
                onChange={(indexName) => setVectorForm({ ...vectorForm, indexName })}
              />
            </div>
            <LabeledInput
              label="API Key"
              hint={
                data.externalConnections.vectorDatabase.apiKeyConfigured
                  ? '已配置，留空不修改'
                  : '未配置，请粘贴 key'
              }
              type="password"
              value={vectorForm.apiKey ?? ''}
              onChange={(apiKey) => setVectorForm({ ...vectorForm, apiKey })}
            />
            <div className="grid gap-3 sm:grid-cols-4">
              <NumberField
                label="召回数量"
                value={vectorForm.searchLimit ?? 5}
                min={1}
                max={100}
                step={1}
                onChange={(searchLimit) => setVectorForm({ ...vectorForm, searchLimit })}
              />
              <NumberField
                label="主判断阈值"
                value={vectorForm.primaryMinScore ?? 0.34}
                min={0}
                max={1}
                step={0.01}
                onChange={(primaryMinScore) => setVectorForm({ ...vectorForm, primaryMinScore })}
              />
              <NumberField
                label="兜底阈值"
                value={vectorForm.fallbackMinScore ?? 0.2}
                min={0}
                max={1}
                step={0.01}
                onChange={(fallbackMinScore) => setVectorForm({ ...vectorForm, fallbackMinScore })}
              />
              <NumberField
                label="兜底卖点数"
                value={vectorForm.fallbackMaxMatches ?? 1}
                min={1}
                max={6}
                step={1}
                onChange={(fallbackMaxMatches) => (
                  setVectorForm({ ...vectorForm, fallbackMaxMatches })
                )}
              />
            </div>
            <NumberField
              label="超时秒数"
              value={vectorForm.timeoutSeconds ?? 30}
              min={0.5}
              step={0.5}
              onChange={(timeoutSeconds) => setVectorForm({ ...vectorForm, timeoutSeconds })}
            />
          </div>
          <ConnectionActions
            isSaving={saveVectorMutation.isPending}
            isTesting={testVectorMutation.isPending}
            onSave={() => saveVectorMutation.mutate(vectorForm)}
            onTest={() => testVectorMutation.mutate()}
          />
          <MutationMessage mutation={saveVectorMutation} successText="VikingDB 向量库配置已保存。" />
          <TestMessage mutation={testVectorMutation} />
        </div>
      </div>
      <div className="border-t border-border px-4 py-3 text-xs leading-5 text-muted-foreground">
        推荐当前策略：卖点知识库开启；VikingDB 仅作为 fallback 开启；fallback 阈值 0.20；fallback 卖点数 1。
        图片返回仍只读本地已审核素材关系，因此这里不会直接改变图片事实。
      </div>
    </section>
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
          excludedCredentialIds: slot.excludedCredentialIds,
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
        title="模型位置配置"
        description="搜索链路只把 API 放在解释和 Agent 两个位置；火山命中卖点、本地取图库不经过这里。"
      />
      <div className="border-b border-border bg-secondary/55 px-4 py-3 text-sm text-muted-foreground">
        人工指定可设置一个主 API 和多个备用 API；自动选择会从允许自动使用的兼容 API 中分配请求。
        等待上限是该位置从开始到结束的总时间，包含主 API、备用 API、容量等待和重试。
      </div>
      <div className="divide-y divide-border">
        {data.routingSlots.map((slot) => {
          const draft = drafts[slot.task] ?? {};
          const autoEnabled = draft.autoSelectEnabled ?? slot.autoSelectEnabled;
          const assignableCredentials = credentialOptions.filter((item) => item.status !== 'disabled');
          return (
            <div key={slot.task} className="api-routing-row text-sm">
              <div className="api-routing-copy min-w-0">
                <div className="font-medium text-foreground">{slot.label}</div>
                <div className="mt-1 text-xs text-muted-foreground">{slot.task}</div>
                <div className="mt-2 text-xs leading-5 text-muted-foreground">
                  {routingSlotDescriptions[slot.task] ?? '当前模型位置。'}
                </div>
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
                  <span>{autoEnabled ? '当前位置自动选择' : '当前位置人工指定'}</span>
                </button>
                <div className="api-routing-field">
                  <span className="api-routing-field-label">固定主 API</span>
                  <Select
                    value={draft.primaryCredentialId ?? ''}
                    onChange={(event) => setDraft(slot.task, { primaryCredentialId: event.target.value })}
                    disabled={autoEnabled}
                    className="bg-white/80"
                  >
                    <option value="">不固定 API</option>
                    {assignableCredentials.map((item) => (
                      <option key={item.id} value={item.id}>{displayCredentialLabel(item)}</option>
                    ))}
                  </Select>
                  <span className="text-[11px] leading-4 text-muted-foreground">
                    优先使用主 API，其他 API 可在备用池中多选；保存后生效。
                  </span>
                </div>
                <BackupPicker
                  credentials={assignableCredentials}
                  selected={draft.backupCredentialIds ?? []}
                  onChange={(backupCredentialIds) => setDraft(slot.task, { backupCredentialIds })}
                  disabled={autoEnabled}
                />
                <BlockedApiPicker
                  credentials={assignableCredentials}
                  selected={draft.excludedCredentialIds ?? []}
                  onChange={(excludedCredentialIds) => (
                    setDraft(slot.task, { excludedCredentialIds })
                  )}
                  disabled={!autoEnabled}
                />
                <div className="api-routing-actions">
                  <label className="api-routing-field">
                    <span className="api-routing-field-label">任务总等待上限（秒）</span>
                    <Input
                      className="bg-white/80"
                      type="number"
                      min={1}
                      value={draft.timeoutSeconds ?? slot.timeoutSeconds}
                      onChange={(event) => setDraft(slot.task, { timeoutSeconds: Number(event.target.value) })}
                    />
                    <span className="text-[11px] leading-4 text-muted-foreground">
                      当前位置全部尝试合计，通常无需修改。
                    </span>
                  </label>
                  <label className="api-routing-field">
                    <span className="api-routing-field-label">接力延迟（毫秒）</span>
                    <Input
                      className="bg-white/80"
                      type="number"
                      min={0}
                      value={draft.hedgingDelayMs ?? slot.hedgingDelayMs}
                      onChange={(event) => setDraft(slot.task, { hedgingDelayMs: Number(event.target.value) })}
                    />
                    <span className="text-[11px] leading-4 text-muted-foreground">
                      首个候选超过该时间未返回时，允许启动下一个候选。
                    </span>
                  </label>
                  <label className="api-routing-field">
                    <span className="api-routing-field-label">并行接力数</span>
                    <Input
                      className="bg-white/80"
                      type="number"
                      min={1}
                      max={4}
                      value={draft.maxParallel ?? slot.maxParallel}
                      onChange={(event) => setDraft(slot.task, { maxParallel: Number(event.target.value) })}
                    />
                    <span className="text-[11px] leading-4 text-muted-foreground">
                      允许同时等待的候选数；未返回的上游不保证被撤销。
                    </span>
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
    ? '当前位置自动选择时由系统决定'
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
        备用 API（可多选）
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
        <PopoverContent align="start" className="w-[22rem] max-w-[calc(100vw-2rem)] rounded-xl p-2">
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

function BlockedApiPicker({
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
    ? '人工指定时不使用屏蔽名单'
    : selectedCredentials.length
      ? `已排除 ${selectedCredentials.length} 个 API`
      : '未排除 API';

  const toggleCredential = (credentialId: string) => {
    onChange(
      selected.includes(credentialId)
        ? selected.filter((id) => id !== credentialId)
        : [...selected, credentialId],
    );
  };

  return (
    <div className={`api-routing-field api-backup-picker ${disabled ? 'is-disabled' : ''}`}>
      <div className="api-routing-field-label">本任务自动排除</div>
      <Popover>
        <PopoverTrigger asChild>
          <button
            type="button"
            className="api-backup-trigger"
            disabled={disabled || !credentials.length}
          >
            <span>{summary}</span>
            <Ban className="size-4 text-muted-foreground" />
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
                    <span className="block truncate text-sm text-foreground">
                      {displayCredentialLabel(item)}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {item.modelName} · {item.autoAssignEnabled ? '可进入自动候选' : '仅人工使用'}
                    </span>
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

function HealthChecks({
  data,
  onOpenTraces,
}: {
  data: ApiCenterSummary;
  onOpenTraces: () => void;
}) {
  const queryClient = useQueryClient();
  const [credentialId, setCredentialId] = useState(data.credentials[0]?.id ?? '');
  const [task, setTask] = useState<ModelTaskName>('search_result_recommendation_reason');
  const activeCredentials = data.credentials.filter((item) => item.status !== 'disabled');
  const runAllMutation = useMutation({
    mutationFn: () => runApiHealthChecks(
      { includeDisabled: false },
      activeCredentials.length,
    ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });
  const maintenanceMutation = useMutation({
    mutationFn: () => runApiCenterMaintenance(
      Math.min(
        Math.max(data.maintenance.maxCredentialsPerCycle, 1),
        activeCredentials.length || 1,
      ),
    ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });
  const testMutation = useMutation({
    mutationFn: () => testApiCredential(
      credentialId,
      task,
    ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-center-summary'] }),
  });

  useEffect(() => {
    if (!credentialId && data.credentials[0]?.id) {
      setCredentialId(data.credentials[0].id);
    }
  }, [credentialId, data.credentials]);

  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader
        title="健康度监测"
        description="这里管理真实调用自动回写、一键巡检和单个 API 测试；每次巡检的详细调用记录统一放在调用链路日志。"
      />
      {(runAllMutation.isSuccess || testMutation.isSuccess || maintenanceMutation.isSuccess) && (
        <div className="border-b border-border bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {maintenanceMutation.data
            ? `后台维护完成：抽检 ${maintenanceMutation.data.checkedCount} 个，健康 ${maintenanceMutation.data.okCount} 个，清理调用日志 ${maintenanceMutation.data.deletedCallTraceCount} 条。`
            : runAllMutation.data
            ? `巡检完成：共 ${runAllMutation.data.checkedCount} 个，健康 ${runAllMutation.data.okCount} 个，异常 ${runAllMutation.data.failedCount} 个。`
            : '单个 API 测试完成。'}
        </div>
      )}
      {(runAllMutation.isError || testMutation.isError || maintenanceMutation.isError) && (
        <div className="border-b border-border bg-red-50 px-4 py-3 text-sm text-red-700">
          {healthCheckErrorMessage(
            runAllMutation.error ?? testMutation.error ?? maintenanceMutation.error,
          )}
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
            系统会用独立的 60 秒窗口执行最小 JSON 探针，不受 API 当前单次调用上限影响。
            瞬时网络或上游错误会自动再试一次；成功后按真实耗时自动校准，无需手动调整秒数。
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
                {Object.entries(currentTaskLabels).map(([value, label]) => (
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
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-foreground">后台维护</h3>
            <Badge
              variant="outline"
              className={data.maintenance.enabled ? statusClass.ok : statusClass.disabled}
            >
              {data.maintenance.enabled ? '已启用' : '未启用'}
            </Badge>
          </div>
          <dl className="mt-3 grid gap-2 text-xs">
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">巡检节奏</dt>
              <dd className="font-medium text-foreground">
                每 {data.maintenance.intervalMinutes} 分钟 · 单轮最多 {data.maintenance.maxCredentialsPerCycle} 个
              </dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">日志保留</dt>
              <dd className="font-medium text-foreground">
                链路 {data.maintenance.callTraceRetentionDays} 天 · 健康 {data.maintenance.healthCheckRetentionDays} 天
              </dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">上次结果</dt>
              <dd className="font-medium text-foreground">
                {maintenanceStatusLabel(data.maintenance.lastStatus)}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">上次完成</dt>
              <dd className="font-medium text-foreground">
                {formatDateTime(data.maintenance.lastFinishedAt)}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">下次预计</dt>
              <dd className="font-medium text-foreground">
                {formatDateTime(data.maintenance.nextRunAt)}
              </dd>
            </div>
          </dl>
          <div className="mt-3 rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            最近抽检 {data.maintenance.lastCheckedCount} 个，
            清理调用日志 {data.maintenance.lastDeletedCallTraceCount} 条，
            清理健康记录 {data.maintenance.lastDeletedHealthCheckCount} 条。
          </div>
          {data.maintenance.lastError ? (
            <p className="mt-2 text-xs text-red-700">{data.maintenance.lastError}</p>
          ) : null}
          <Button
            className="mt-3 w-full"
            variant="outline"
            size="sm"
            disabled={!activeCredentials.length || maintenanceMutation.isPending}
            onClick={() => maintenanceMutation.mutate()}
          >
            {maintenanceMutation.isPending ? '维护中...' : '立即执行后台维护'}
          </Button>
        </div>

      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3">
        <p className="text-xs text-muted-foreground">
          巡检的 Provider、模型、任务、状态、耗时和错误摘要，统一记录在调用链路日志中。
        </p>
        <Button variant="outline" size="sm" onClick={onOpenTraces}>
          <ListTree className="size-4" />
          查看调用链路日志
        </Button>
      </div>
    </section>
  );
}

function CallTraces({ data }: { data: ApiCenterSummary }) {
  const pageSize = 50;
  const [filters, setFilters] = useState({
    keyword: '',
    requestId: '',
    task: '',
    status: '',
    provider: '',
    credentialId: '',
  });
  const [appliedFilters, setAppliedFilters] = useState(filters);
  const [offset, setOffset] = useState(0);
  const tracesQuery = useQuery({
    queryKey: ['api-call-traces', appliedFilters, offset],
    queryFn: () => fetchApiCallTraces({
      ...appliedFilters,
      limit: pageSize,
      offset,
    }),
  });
  const rows = tracesQuery.data?.items ?? data.recentCallTraces.slice(0, 80);
  const total = tracesQuery.data?.total ?? rows.length;
  const hasMore = tracesQuery.data?.hasMore ?? false;
  const applyFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setOffset(0);
    setAppliedFilters(filters);
  };
  const resetFilters = () => {
    const next = {
      keyword: '',
      requestId: '',
      task: '',
      status: '',
      provider: '',
      credentialId: '',
    };
    setFilters(next);
    setAppliedFilters(next);
    setOffset(0);
  };
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader
        title="全项目 API 调用链路"
        description="这里显示当前两个模型位置和历史退役任务的调用记录；不包含完整密钥、Prompt、图片或聊天正文。"
      />
      <form
        className="grid gap-3 border-b border-border bg-muted/20 px-4 py-3 md:grid-cols-[1.2fr_1fr_1fr_1fr] xl:grid-cols-[1.2fr_1fr_1fr_1fr_1fr_auto]"
        onSubmit={applyFilters}
      >
        <Input
          value={filters.keyword}
          onChange={(event) => setFilters((current) => ({
            ...current,
            keyword: event.target.value,
          }))}
          placeholder="搜索关键词 / 错误码 / 摘要"
        />
        <Input
          value={filters.requestId}
          onChange={(event) => setFilters((current) => ({
            ...current,
            requestId: event.target.value,
          }))}
          placeholder="请求 ID"
        />
        <Select
          value={filters.task}
          onChange={(event) => setFilters((current) => ({
            ...current,
            task: event.target.value,
          }))}
        >
          <option value="">全部任务</option>
          <optgroup label="当前模型位置">
            {Object.entries(currentTaskLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </optgroup>
        </Select>
        <Select
          value={filters.status}
          onChange={(event) => setFilters((current) => ({
            ...current,
            status: event.target.value,
          }))}
        >
          <option value="">全部状态</option>
          <option value="ok">OK</option>
          <option value="failed">失败</option>
          <option value="timed_out">超时</option>
          <option value="skipped">未配置/跳过</option>
        </Select>
        <Select
          value={filters.credentialId || (filters.provider ? `provider:${filters.provider}` : '')}
          onChange={(event) => {
            const value = event.target.value;
            if (value.startsWith('provider:')) {
              setFilters((current) => ({
                ...current,
                provider: value.slice('provider:'.length),
                credentialId: '',
              }));
              return;
            }
            setFilters((current) => ({
              ...current,
              provider: '',
              credentialId: value,
            }));
          }}
        >
          <option value="">全部中转站/API</option>
          {data.providerGroups.map((group) => (
            <option key={group.providerGroup} value={`provider:${group.providerGroup}`}>
              中转站：{group.providerGroup}
            </option>
          ))}
          {data.credentials.map((credential) => (
            <option key={credential.id} value={credential.id}>
              API：{displayCredentialLabel(credential)}
            </option>
          ))}
        </Select>
        <div className="flex gap-2">
          <Button type="submit" size="sm" className="flex-1" disabled={tracesQuery.isFetching}>
            筛选
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={resetFilters}>
            重置
          </Button>
        </div>
      </form>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="border-b border-border bg-muted/40 text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">时间</th>
              <th className="px-4 py-3 font-medium">所属请求</th>
              <th className="px-4 py-3 font-medium">位置</th>
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
                <td className="max-w-[260px] px-4 py-3 text-xs">
                  <div className="truncate font-medium text-foreground" title={traceContextLabel(item)}>
                    {traceContextLabel(item)}
                  </div>
                  {item.searchKeyword && item.searchResultCount != null ? (
                    <div className="mt-1 text-[11px] text-muted-foreground">
                      结果已返回 {item.searchResultCount} 张
                      {item.searchTimedOut ? ' · 部分增强超时' : ''}
                    </div>
                  ) : null}
                  {item.requestId ? (
                    <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                      {item.requestId.slice(0, 8)}
                    </div>
                  ) : null}
                </td>
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
                <td className="px-4 py-3 text-xs text-muted-foreground">
                  <TraceErrorDetail item={item} />
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan={8}><Empty text="暂无 API 调用记录。项目中的任一模型/API 调用完成后都会出现在这里。" /></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3 text-xs text-muted-foreground">
        <span>
          共 {total} 条
          {tracesQuery.isFetching ? ' · 正在刷新' : ''}
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={offset <= 0 || tracesQuery.isFetching}
            onClick={() => setOffset((current) => Math.max(0, current - pageSize))}
          >
            上一页
          </Button>
          <span>{Math.floor(offset / pageSize) + 1}</span>
          <Button
            variant="outline"
            size="sm"
            disabled={!hasMore || tracesQuery.isFetching}
            onClick={() => setOffset((current) => current + pageSize)}
          >
            下一页
          </Button>
        </div>
      </div>
    </section>
  );
}

function TraceErrorDetail({ item }: { item: ApiCallTrace }) {
  if (!item.errorCode && !item.errorSummary) return <>—</>;
  return (
    <div className="space-y-1.5">
      {item.errorCode ? (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-mono text-[11px] text-foreground">{item.errorCode}</span>
          {item.errorCategory ? (
            <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-600">
              {errorCategoryLabel[item.errorCategory] ?? item.errorCategory}
            </Badge>
          ) : null}
          {item.errorSeverity ? (
            <Badge
              variant="outline"
              className={errorSeverityClass[item.errorSeverity] ?? errorSeverityClass.warning}
            >
              {errorSeverityLabel[item.errorSeverity] ?? item.errorSeverity}
            </Badge>
          ) : null}
          {item.errorRetryable != null ? (
            <Badge variant="outline" className="border-border bg-card text-muted-foreground">
              {item.errorRetryable ? '可重试/可换候选' : '不盲目重试'}
            </Badge>
          ) : null}
        </div>
      ) : null}
      {item.errorSummary ? <div>{item.errorSummary}</div> : null}
      {item.errorSystemAction ? (
        <div className="text-[11px] text-muted-foreground">
          系统：{item.errorSystemAction}
        </div>
      ) : null}
      {item.errorOperatorAction ? (
        <div className="text-[11px] text-muted-foreground">
          建议：{item.errorOperatorAction}
        </div>
      ) : null}
    </div>
  );
}

function traceContextLabel(item: ApiCallTrace): string {
  if (item.searchKeyword) return `搜索：${item.searchKeyword}`;
  if (item.outputSummary.kind === 'health_check') return '健康检查';
  if (item.outputSummary.kind === 'temperature_probe') return '温度探测';
  if (item.requestId) return '业务请求';
  return '历史独立调用';
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

function providerGroupStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ok: '稳定',
    watch: '观察',
    degraded: '建议处理',
  };
  return labels[status] ?? status;
}

function capabilityStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ok: '可用',
    failed: '不匹配',
    unknown: '未检测',
  };
  return labels[status] ?? status;
}

function capabilityTooltip(capability: ApiCredential['capabilityProfile'][number]): string {
  const parts = [
    `${capability.label}: ${capabilityStatusLabel(capability.status)}`,
    capability.lastTask ? `最近任务：${taskLabels[capability.lastTask] ?? capability.lastTask}` : '',
    capability.durationMs != null ? `耗时：${capability.durationMs}ms` : '',
    capability.errorSummary ? `摘要：${capability.errorSummary}` : '',
    capability.checkedAt ? `检测时间：${new Date(capability.checkedAt).toLocaleString('zh-CN')}` : '',
  ].filter(Boolean);
  return parts.join('\n');
}

function formatPercent(value: number): string {
  return `${Math.round((value || 0) * 100)}%`;
}

function temperatureTuneMessage(result: ApiTemperatureTuneResult): string {
  if (result.status !== 'ok' || result.selectedTemperatureEnabled == null) {
    const lastProbe = result.probes.at(-1);
    return lastProbe?.errorSummary
      ? `测试未通过：${lastProbe.errorSummary}`
      : `测试未通过：已检查 ${result.probes.length} 种参数设置。`;
  }
  if (!result.selectedTemperatureEnabled) {
    return '测试通过：该模型不接受 temperature，保存后将自动不发送此参数。';
  }
  if (result.selectedTemperature === result.previousTemperature) {
    return `温度匹配完成：当前 ${result.selectedTemperature} 可用，已保持原设置。`;
  }
  return `温度匹配完成：已从 ${result.previousTemperature} 调整为 ${result.selectedTemperature}。`;
}

function maintenanceStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    idle: '尚未运行',
    running: '正在运行',
    ok: '运行正常',
    failed: '运行失败',
  };
  return labels[status] ?? status;
}

function formatDateTime(value?: string | null): string {
  return value ? new Date(value).toLocaleString('zh-CN') : '暂无';
}

function healthCheckErrorMessage(error: unknown): string {
  const apiError = getApiError(error);
  if (apiError.code === 'request_timeout') {
    return '页面等待巡检结果超过预计时间。后台检测可能仍在继续，请稍后刷新或查看调用链路；这不代表 API 已停用，也不需要修改调用上限。';
  }
  return apiError.message;
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

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <label className="grid gap-1.5 text-sm">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <Input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function SwitchField({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (value: boolean) => void;
}) {
  return (
    <button
      type="button"
      className="pc-switch rounded-xl border border-border bg-muted/30 px-3 py-2"
      data-checked={checked}
      onClick={() => onChange(!checked)}
      aria-pressed={checked}
    >
      <span className="pc-switch-track" />
      <span>{label}</span>
    </button>
  );
}

function SearchChainDiagnosticPanel({
  result,
}: {
  result: ApiSearchChainDiagnosticResult;
}) {
  const className = result.status === 'ok'
    ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
    : result.status === 'degraded'
      ? 'border-amber-200 bg-amber-50 text-amber-800'
      : result.status === 'failed'
      ? 'border-red-200 bg-red-50 text-red-700'
      : 'border-slate-200 bg-slate-50 text-slate-600';
  return (
    <div className="mt-4 grid gap-3">
      <div className={`rounded-xl border px-3 py-2 text-xs leading-5 ${className}`}>
        <div className="font-medium">
          {statusLabel[result.status] ?? result.status}
          {' · '}
          {result.durationMs}ms
        </div>
        <div>
          {result.status === 'ok'
            ? `完整链路已跑通，命中 ${result.matchedConcepts.length} 个卖点，返回 ${result.resultCount} 张图。`
            : result.status === 'degraded'
              ? `最终搜索可用，命中 ${result.matchedConcepts.length} 个卖点，返回 ${result.resultCount} 张图；但至少一个上游步骤需要处理。`
            : '完整链路没有稳定跑通，请按下面步骤定位问题。'}
        </div>
        {result.fallback || result.fallbackReason ? (
          <div>
            兜底状态：{result.fallback ? '已触发 VikingDB fallback' : '未触发 fallback'}
            {result.fallbackReason ? ` · ${result.fallbackReason}` : ''}
          </div>
        ) : null}
        {result.matchedConcepts.length ? (
          <div>命中卖点：{result.matchedConcepts.join('、')}</div>
        ) : null}
      </div>
      <div className="grid gap-2">
        {result.steps.map((step) => (
          <div
            key={step.name}
            className="rounded-xl border border-border bg-muted/30 px-3 py-2 text-xs leading-5"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium text-foreground">{step.name}</span>
              <Badge variant="outline" className={statusClass[step.status] ?? ''}>
                {statusLabel[step.status] ?? step.status}
              </Badge>
              <span className="text-muted-foreground">{step.durationMs}ms</span>
            </div>
            <div className="mt-1 text-muted-foreground">{step.message}</div>
            {Object.keys(step.preview ?? {}).length ? (
              <pre className="mt-2 max-h-36 overflow-auto whitespace-pre-wrap rounded-lg bg-white/70 p-2 text-[11px] text-slate-700">
                {JSON.stringify(step.preview, null, 2)}
              </pre>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function ConnectionActions({
  isSaving,
  isTesting,
  onSave,
  onTest,
}: {
  isSaving: boolean;
  isTesting: boolean;
  onSave: () => void;
  onTest: () => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      <Button size="sm" disabled={isSaving} onClick={onSave}>
        <Save className="size-4" />
        {isSaving ? '保存中...' : '保存配置'}
      </Button>
      <Button variant="outline" size="sm" disabled={isTesting} onClick={onTest}>
        <Sparkles className="size-4" />
        {isTesting ? '测试中...' : '测试连接'}
      </Button>
    </div>
  );
}

function MutationMessage({
  mutation,
  successText,
}: {
  mutation: { isSuccess: boolean; isError: boolean; error: unknown };
  successText: string;
}) {
  if (mutation.isSuccess) {
    return <p className="mt-3 text-sm text-emerald-700">{successText}</p>;
  }
  if (mutation.isError) {
    return (
      <p className="mt-3 text-sm text-destructive">
        {getApiError(mutation.error).message}
      </p>
    );
  }
  return null;
}

function TestMessage({
  mutation,
}: {
  mutation: {
    isSuccess: boolean;
    isError: boolean;
    error: unknown;
    data?: ApiExternalConnectionTestResult;
  };
}) {
  if (mutation.isError) {
    return (
      <p className="mt-3 text-sm text-destructive">
        {getApiError(mutation.error).message}
      </p>
    );
  }
  if (!mutation.isSuccess || !mutation.data) return null;
  const className = mutation.data.status === 'ok'
    ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
    : mutation.data.status === 'failed'
      ? 'border-red-200 bg-red-50 text-red-700'
      : 'border-slate-200 bg-slate-50 text-slate-600';
  return (
    <div className={`mt-3 rounded-xl border px-3 py-2 text-xs leading-5 ${className}`}>
      <div className="font-medium">
        {statusLabel[mutation.data.status] ?? mutation.data.status}
        {' · '}
        {mutation.data.durationMs}ms
      </div>
      <div>{mutation.data.message}</div>
      {Object.keys(mutation.data.preview ?? {}).length ? (
        <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap rounded-lg bg-white/60 p-2 text-[11px] text-slate-700">
          {JSON.stringify(mutation.data.preview, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="px-4 py-5 text-sm text-muted-foreground">{text}</p>;
}
