import { useEffect, useMemo, useState } from 'react';
import { Check, Pencil, Plus, RotateCcw, X } from 'lucide-react';
import { toast } from 'sonner';

import { getApiError } from '@client/src/api/client';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { Select } from '@client/src/components/ui/select';
import { splitAcceptedConceptPhrases } from '@client/src/features/assets/conceptPhrasePresentation';
import { useBusinessConceptActions } from '@client/src/features/assets/useBusinessConceptActions';
import type { BusinessConcept, ConceptPhraseType, ConceptSearchPhrase } from '@client/src/types/api';

const TYPE_LABELS: Record<ConceptPhraseType, string> = {
  official: '标准表达',
  alias: '别名',
  pain: '痛点',
  outcome: '结果诉求',
  scenario: '使用场景',
  colloquial: '口语说法',
  typo: '常见错字',
};

const ORIGIN_LABELS: Record<ConceptSearchPhrase['origin'], string> = {
  source_document: '初始词库',
  manual: '人工补充',
  ai: 'AI建议',
  search_feedback: '搜索反馈',
  migrated: '历史迁移',
};

export default function ConceptPhraseEditor({ concept }: { concept: BusinessConcept }) {
  const actions = useBusinessConceptActions();
  const [newPhrase, setNewPhrase] = useState('');
  const [phraseType, setPhraseType] = useState<ConceptPhraseType>('colloquial');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState('');
  useEffect(() => {
    setEditingId(null);
    setEditingValue('');
  }, [concept.id]);

  const groups = useMemo(() => {
    const accepted = splitAcceptedConceptPhrases(concept.searchPhrases);
    return {
      publicPhrases: accepted.publicPhrases,
      keywords: accepted.keywords,
      pending: concept.searchPhrases.filter((item) => item.reviewStatus === 'pending'),
      inactive: concept.searchPhrases.filter((item) => item.reviewStatus === 'rejected'),
    };
  }, [concept.searchPhrases]);

  const addPhrase = async () => {
    if (!newPhrase.trim()) return;
    try {
      await actions.addPhrase.mutateAsync({
        conceptId: concept.id,
        input: {
          phrase: newPhrase.trim(),
          phraseType,
          origin: 'manual',
          reviewStatus: 'accepted',
          weight: 1,
        },
      });
      setNewPhrase('');
      toast.success('公共话术已添加，并会被关联素材共同复用');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  const updatePhrase = async (
    phrase: ConceptSearchPhrase,
    input: { phrase?: string; reviewStatus?: 'accepted' | 'rejected' },
  ) => {
    try {
      await actions.updatePhrase.mutateAsync({
        conceptId: concept.id,
        phraseId: phrase.id,
        input,
      });
      setEditingId(null);
      toast.success(input.reviewStatus === 'rejected' ? '公共话术已停用' : '公共话术已更新');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-primary/15 bg-accent/45 p-4">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            value={newPhrase}
            onChange={(event) => setNewPhrase(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && newPhrase.trim()) addPhrase();
            }}
            placeholder={`补充一种搜索“${concept.name}”的公共说法`}
            maxLength={300}
            className="bg-card sm:min-w-0 sm:flex-1"
          />
          <div className="shrink-0 sm:w-40">
            <Select
              value={phraseType}
              onChange={(event) => setPhraseType(event.target.value as ConceptPhraseType)}
            >
              {Object.entries(TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </Select>
          </div>
          <Button className="shrink-0" onClick={addPhrase} disabled={!newPhrase.trim() || actions.addPhrase.isPending}>
            <Plus className="size-4" />添加公共话术
          </Button>
        </div>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          这里只添加适用于该卖点下多张素材的通用说法；具体画面、文案和版本差异留在素材详情。
        </p>
      </section>

      <PhraseGroup
        title={`已启用公共话术 · ${groups.publicPhrases.length}`}
        emptyText="还没有公共话术，可以从真实业务搜索说法开始补充。"
        phrases={groups.publicPhrases}
        editingId={editingId}
        editingValue={editingValue}
        onEditingValueChange={setEditingValue}
        onEdit={(phrase) => {
          setEditingId(phrase.id);
          setEditingValue(phrase.phrase);
        }}
        onCancel={() => setEditingId(null)}
        onSave={(phrase) => updatePhrase(phrase, { phrase: editingValue.trim() })}
        onToggle={(phrase) => updatePhrase(phrase, { reviewStatus: 'rejected' })}
      />

      {groups.keywords.length > 0 && (
        <PhraseGroup
          title={`辅助关键词 · ${groups.keywords.length}`}
          description="仅帮助“教材、版本、章节”等短词精确召回，不等同于完整业务话术。"
          emptyText=""
          phrases={groups.keywords}
          editingId={editingId}
          editingValue={editingValue}
          onEditingValueChange={setEditingValue}
          onEdit={(phrase) => {
            setEditingId(phrase.id);
            setEditingValue(phrase.phrase);
          }}
          onCancel={() => setEditingId(null)}
          onSave={(phrase) => updatePhrase(phrase, { phrase: editingValue.trim() })}
          onToggle={(phrase) => updatePhrase(phrase, { reviewStatus: 'rejected' })}
          collapsible
        />
      )}

      {groups.pending.length > 0 && (
        <PhraseGroup
          title={`待确认候选 · ${groups.pending.length}`}
          description="AI建议和搜索反馈候选在确认前不会作为正式公共话术使用。"
          emptyText=""
          phrases={groups.pending}
          editingId={null}
          editingValue=""
          onEditingValueChange={() => undefined}
          onEdit={() => undefined}
          onCancel={() => undefined}
          onSave={() => undefined}
          onToggle={(phrase) => updatePhrase(phrase, { reviewStatus: 'accepted' })}
          onReject={(phrase) => updatePhrase(phrase, { reviewStatus: 'rejected' })}
          mode="pending"
        />
      )}

      {groups.inactive.length > 0 && (
        <PhraseGroup
          title={`已停用 · ${groups.inactive.length}`}
          emptyText=""
          phrases={groups.inactive}
          editingId={null}
          editingValue=""
          onEditingValueChange={() => undefined}
          onEdit={() => undefined}
          onCancel={() => undefined}
          onSave={() => undefined}
          onToggle={(phrase) => updatePhrase(phrase, { reviewStatus: 'accepted' })}
          mode="inactive"
        />
      )}
    </div>
  );
}

interface PhraseGroupProps {
  title: string;
  emptyText: string;
  phrases: ConceptSearchPhrase[];
  editingId: string | null;
  editingValue: string;
  mode?: 'active' | 'pending' | 'inactive';
  description?: string;
  collapsible?: boolean;
  onEditingValueChange: (value: string) => void;
  onEdit: (phrase: ConceptSearchPhrase) => void;
  onCancel: () => void;
  onSave: (phrase: ConceptSearchPhrase) => void;
  onToggle: (phrase: ConceptSearchPhrase) => void;
  onReject?: (phrase: ConceptSearchPhrase) => void;
}

function PhraseGroup(props: PhraseGroupProps) {
  const mode = props.mode ?? 'active';
  const rows = (
      <div className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
        {props.phrases.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-muted-foreground">{props.emptyText}</p>
        ) : props.phrases.map((phrase) => (
          <div key={phrase.id} className="flex items-center gap-3 px-4 py-3">
            {props.editingId === phrase.id ? (
              <>
                <Input
                  autoFocus
                  value={props.editingValue}
                  onChange={(event) => props.onEditingValueChange(event.target.value)}
                  className="h-9 flex-1"
                />
                <Button size="icon" variant="ghost" onClick={() => props.onSave(phrase)} disabled={!props.editingValue.trim()}>
                  <Check className="size-4" />
                </Button>
                <Button size="icon" variant="ghost" onClick={props.onCancel}>
                  <X className="size-4" />
                </Button>
              </>
            ) : (
              <>
                <span className={`min-w-0 flex-1 text-sm ${mode === 'inactive' ? 'text-muted-foreground line-through' : ''}`}>
                  {phrase.phrase}
                </span>
                <Badge variant="outline" className="hidden shrink-0 sm:inline-flex">
                  {TYPE_LABELS[phrase.phraseType]}
                </Badge>
                <Badge variant="secondary" className="hidden shrink-0 md:inline-flex">
                  {ORIGIN_LABELS[phrase.origin]}
                </Badge>
                {mode === 'active' && !['source_document', 'migrated'].includes(phrase.origin) && (
                  <Button size="icon" variant="ghost" onClick={() => props.onEdit(phrase)} title="修改话术">
                    <Pencil className="size-4" />
                  </Button>
                )}
                {mode === 'pending' ? (
                  <>
                    <Button size="icon" variant="ghost" onClick={() => props.onToggle(phrase)} title="确认启用">
                      <Check className="size-4" />
                    </Button>
                    <Button size="icon" variant="ghost" onClick={() => props.onReject?.(phrase)} title="拒绝候选">
                      <X className="size-4" />
                    </Button>
                  </>
                ) : (
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => props.onToggle(phrase)}
                    title={mode === 'inactive' ? '重新启用' : '停用话术'}
                  >
                    {mode === 'inactive' ? <RotateCcw className="size-4" /> : <X className="size-4" />}
                  </Button>
                )}
              </>
            )}
          </div>
        ))}
      </div>
  );

  if (props.collapsible) {
    return (
      <details className="rounded-2xl border border-border bg-secondary/35 p-3">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          {props.title}
          {props.description && <span className="ml-2 normal-case tracking-normal">{props.description}</span>}
        </summary>
        <div className="mt-3">{rows}</div>
      </details>
    );
  }

  return (
    <section>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {props.title}
      </h3>
      {props.description && <p className="mb-2 text-xs text-muted-foreground">{props.description}</p>}
      {rows}
    </section>
  );
}
