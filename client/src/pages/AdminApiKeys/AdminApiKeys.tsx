import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Copy, KeyRound, Plus, ShieldOff } from 'lucide-react';
import { toast } from 'sonner';

import * as adminApi from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { copyTextToClipboard } from '@client/src/lib/clipboard';

export default function AdminApiKeys() {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [secret, setSecret] = useState<string | null>(null);
  const keys = useQuery({ queryKey: ['admin-api-keys'], queryFn: adminApi.fetchExternalApiKeys });
  const create = useMutation({
    mutationFn: () => adminApi.createExternalApiKey({ name: name.trim() }),
    onSuccess: (created) => {
      setName('');
      setSecret(created.secret);
      void queryClient.invalidateQueries({ queryKey: ['admin-api-keys'] });
      toast.success('API Key 已创建，请立即复制保存');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });
  const revoke = useMutation({
    mutationFn: adminApi.revokeExternalApiKey,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin-api-keys'] });
      toast.success('API Key 已撤销');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });
  const copy = async (value: string, message: string) => {
    if (await copyTextToClipboard(value)) toast.success(message);
    else toast.error('复制失败，请手动选择');
  };

  return (
    <div className="page-shell max-w-6xl">
      <PageHeader title="开放 API" description="为其他项目创建服务端访问密钥。原始密钥只显示一次，请交给对方后端保存。" />
      <section className="surface-card mt-7 p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="flex size-10 items-center justify-center rounded-xl bg-accent text-primary"><Plus className="size-5" /></div>
          <div><h2 className="font-semibold">创建 API Key</h2><p className="mt-1 text-xs text-muted-foreground">默认每分钟最多调用 60 次，可随时撤销。</p></div>
        </div>
        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex-1"><span className="field-label">用途名称</span><Input value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：官网 AI 配图" /></label>
          <Button disabled={create.isPending || name.trim().length < 1} onClick={() => create.mutate()}><KeyRound className="size-4" />生成密钥</Button>
        </div>
        {secret && (
          <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
            <div className="font-medium">请现在复制密钥</div><p className="mt-1 text-xs text-amber-900/75">关闭此页面后无法再次查看完整密钥。</p>
            <div className="mt-3 flex items-center gap-2"><code className="min-w-0 flex-1 break-all rounded-lg bg-white/80 px-3 py-2 text-xs">{secret}</code><Button size="sm" variant="outline" onClick={() => void copy(secret, 'API Key 已复制')}><Copy className="size-4" />复制</Button></div>
          </div>
        )}
      </section>
      <section className="surface-card mt-6 overflow-hidden">
        <div className="flex items-center justify-between border-b border-border/80 px-5 py-4"><div><h2 className="font-semibold">已创建的密钥</h2><p className="mt-1 text-xs text-muted-foreground">列表只显示前缀和状态，不会显示完整密钥。</p></div>{keys.data && <Badge variant="secondary">{keys.data.length} 个</Badge>}</div>
        {keys.isLoading ? <p className="p-6 text-sm text-muted-foreground">正在加载…</p> : keys.isError ? <p className="p-6 text-sm text-destructive">{getApiError(keys.error).message}</p> : keys.data?.length ? keys.data.map((item) => (
          <div key={item.id} className="flex flex-col gap-3 border-b border-border/70 px-5 py-4 last:border-0 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0"><div className="flex items-center gap-2"><KeyRound className="size-4 text-primary" /><span className="font-medium">{item.name}</span><Badge variant={item.status === 'active' ? 'secondary' : 'outline'}>{item.status === 'active' ? '可用' : item.status === 'expired' ? '已过期' : '已撤销'}</Badge></div><div className="mt-1 text-xs text-muted-foreground"><code>{item.secretPreview}</code> · 每分钟 {item.rateLimitPerMinute} 次 · 创建于 {new Date(item.createdAt).toLocaleString('zh-CN')}</div></div>
            {item.status === 'active' && <Button size="sm" variant="outline" disabled={revoke.isPending} onClick={() => { if (window.confirm(`确定撤销“${item.name}”的 API Key 吗？撤销后无法恢复。`)) revoke.mutate(item.id); }}><ShieldOff className="size-4" />撤销</Button>}
          </div>
        )) : <div className="p-6 text-sm text-muted-foreground">还没有 API Key。</div>}
      </section>
      <section className="mt-6 rounded-xl border border-border/70 bg-secondary/30 p-5 text-sm leading-6 text-muted-foreground"><div className="flex items-center gap-2 font-medium text-foreground"><Check className="size-4 text-emerald-600" />接入方式</div><p className="mt-2">外部项目后端请求 <code>POST /api/public/image-search</code>，使用 <code>Authorization: Bearer {'<API_KEY>'}</code>，请求体传入自然语言 <code>query</code> 和可选的 <code>limit</code>、<code>channel</code>、<code>scene</code>。</p></section>
    </div>
  );
}
