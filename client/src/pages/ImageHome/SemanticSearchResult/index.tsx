import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';

import { submitSearchFeedback } from '@client/src/api/image';
import { Button } from '@client/src/components/ui/button';
import { useProjectBasket } from '@client/src/features/assets/useProjectBasket';
import type { SearchFeedbackType, SemanticSearchResponse } from '@client/src/types/api';
import ProjectBasketPanel from './ProjectBasketPanel';
import SearchFeedbackPanel from './SearchFeedbackPanel';
import SearchResultGrid from './SearchResultGrid';
import { searchIntentOptions, searchIntentTitle } from './searchConceptPresentation';
import {
  activeRefinementCount,
  filterResultsByRefinements,
  type SearchRefinements,
} from '../searchResultFilters';

interface SemanticSearchResultProps {
  keyword: string;
  result: SemanticSearchResponse;
  refinements: SearchRefinements;
  showSearchContext: boolean;
  showBusinessAccount: boolean;
  animateGifPreview: boolean;
  onClear: () => void;
}


const SemanticSearchResult = ({
  keyword,
  result,
  refinements,
  showSearchContext,
  showBusinessAccount,
  animateGifPreview,
  onClear,
}: SemanticSearchResultProps) => {
  const [feedbackNote, setFeedbackNote] = useState('');
  const [submittedFeedback, setSubmittedFeedback] = useState<SearchFeedbackType | null>(null);
  const projectBasket = useProjectBasket();
  const matchedSellingPoints = useMemo(
    () => searchIntentOptions(result.searchUnderstanding).map((item) => item.name),
    [result.searchUnderstanding],
  );
  const visibleResults = useMemo(
    () => filterResultsByRefinements(
      result.results,
      refinements,
      { preserveConceptNames: matchedSellingPoints },
    ),
    [matchedSellingPoints, refinements, result.results],
  );
  const refinementCount = activeRefinementCount(refinements);
  const intentTitle = searchIntentTitle(result.searchUnderstanding?.queryType);
  const routeSummary = buildRouteSummary({
    matchedSellingPoints,
    routeExplanation: result.routeExplanation,
  });
  const feedbackMutation = useMutation({
    mutationFn: (feedbackType: SearchFeedbackType) => submitSearchFeedback({
      searchLogId: result.searchLogId,
      keyword,
      feedbackType,
      note: feedbackNote.trim() || undefined,
    }),
    onSuccess: (_data, feedbackType) => {
      setSubmittedFeedback(feedbackType);
      setFeedbackNote('');
    },
  });

  useEffect(() => {
    setFeedbackNote('');
    setSubmittedFeedback(null);
  }, [keyword, result.searchLogId]);

  return (
    <div className="mt-6">
      {showSearchContext && (
        <div className="mb-4 flex items-center justify-between gap-3 border-b border-border/70 pb-3">
          <p className="text-sm text-muted-foreground">
            {refinementCount > 0
              ? `当前显示 ${visibleResults.length} 组，已应用 ${refinementCount} 个渠道/场景筛选`
              : result.matchSummary || `${intentTitle}，找到 ${result.results.length} 组素材`}
          </p>
          <Button variant="ghost" size="sm" onClick={onClear}>
            <X className="mr-1 size-3.5" />
            清除搜索
          </Button>
        </div>
      )}

      {result.fallback && (
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <div>
              <p className="font-medium">部分智能判断链路发生降级，已保留当前可用搜索结果。</p>
              <p className="mt-1">
                {result.fallbackReason || '外部语义增强未在时限内完成，可稍后重试或到 API 中心测试连接。'}
              </p>
            </div>
          </div>
        </div>
      )}

      {routeSummary && (
        <div className="mb-4 rounded-xl border border-foreground/10 bg-foreground px-4 py-3 text-background shadow-sm">
          <div className="space-y-2 text-xs leading-5">
            <p>
              <span className="font-semibold">结果：</span>
              <span>{routeSummary.result}</span>
            </p>
            <p className="text-background/82">
              <span className="font-semibold text-background">判断：</span>
              <span>{routeSummary.judgment}</span>
            </p>
            <p className="text-background/82">
              <span className="font-semibold text-background">定义：</span>
              <span>{routeSummary.definition}</span>
            </p>
          </div>
        </div>
      )}

      {visibleResults.length > 0 ? (
        <>
          <ProjectBasketPanel
            items={projectBasket.items}
            onRemove={projectBasket.remove}
            onClear={projectBasket.clear}
          />
          <SearchResultGrid
            key={`${result.searchLogId ?? keyword}:${visibleResults.length}`}
            items={visibleResults}
            keyword={keyword}
            searchLogId={result.searchLogId}
            showSearchContext={showSearchContext}
            animateGifPreview={animateGifPreview}
            isInProjectBasket={projectBasket.has}
            onToggleProjectBasket={projectBasket.toggle}
          />
        </>
      ) : !result.fallback ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20">
          <p className="text-sm text-muted-foreground">
            {refinementCount > 0
              ? '当前筛选组合下没有素材，可放宽一个条件'
              : (result.searchUnderstanding?.matchedBusinessConcepts.length ?? 0) === 0
                ? '本次没有识别出可靠卖点，暂时没有找到合适素材'
                : '暂时没有找到合适素材'}
          </p>
        </div>
      ) : null}

      {showSearchContext && showBusinessAccount && (
        <SearchFeedbackPanel
          key={result.searchLogId ?? keyword}
          feedbackNote={feedbackNote}
          feedbackMutation={feedbackMutation}
          submittedFeedback={submittedFeedback}
          onFeedbackNoteChange={setFeedbackNote}
        />
      )}
    </div>
  );
};

interface RouteSummaryInput {
  matchedSellingPoints: string[];
  routeExplanation?: string | null;
}

export function buildRouteSummary({
  matchedSellingPoints,
  routeExplanation,
}: RouteSummaryInput): { result: string; judgment: string; definition: string } | null {
  if (matchedSellingPoints.length === 0) return null;
  const sellingPointText = matchedSellingPoints.length > 0
    ? matchedSellingPoints.slice(0, 3).join('、')
    : '当前需求';
  return {
    result: `命中卖点：${sellingPointText}`,
    judgment: cleanRouteExplanation(routeExplanation)
      || '实时判断暂未完成，请重新搜索。',
    definition: buildSellingPointDefinitions(matchedSellingPoints),
  };
}

function cleanRouteExplanation(value?: string | null): string {
  const processMarkers = [
    '未指定渠道',
    '当前返回',
    '卡片下方',
    '已审核素材',
    '保留手机端大图',
    '保留手机端小图',
    '已按当前渠道',
    '渠道/场景筛选',
    '同时按',
    '收窄版位',
  ];
  const explanation = (value ?? '')
    .replace(/<reference\b[^>]*>[\s\S]*?<\/reference>/g, '')
    .replace(/<\/?reference\b[^>]*>/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  const cutoffIndexes = processMarkers
    .map((marker) => explanation.indexOf(marker))
    .filter((index) => index >= 0);
  return (cutoffIndexes.length
    ? explanation.slice(0, Math.min(...cutoffIndexes))
    : explanation
  )
    .replace(/(?:未指定渠道|已按当前渠道\/场景筛选|同时按).+?(?:。|$)/g, '')
    .replace(/当前返回\s*\d+\s*组[^。]*。?/g, '')
    .replace(/卡片下方[^。]*。?/g, '')
    .replace(/相关证明点[:：][\s\S]*$/g, '')
    .replace(/对应[^。]*证明点[:：][\s\S]*$/g, '')
    .replace(/证明点\s*\d+[:：][^。]*。?/g, '')
    .replace(/[，,；; ]+$/g, '')
    .trim();
}

function buildSellingPointDefinitions(matchedSellingPoints: string[]): string {
  const definitions = matchedSellingPoints
    .slice(0, 3)
    .map((name) => {
      const definition = SELLING_POINT_DEFINITIONS[name];
      return definition ? `${name}：${definition}` : `${name}：以知识库中该卖点的业务定义为准。`;
    });
  return definitions.join('；');
}

const SELLING_POINT_DEFINITIONS: Record<string, string> = {
  同步校内: '课程按孩子所在地区和学校使用的教材版本、目录及章节进度对应，减少校内外版本不一致、章节对不上的问题。',
  教材版本与课程目录同步: '课程按孩子所在地区和学校使用的教材版本、目录及章节进度对应，减少校内外版本不一致、章节对不上的问题。',
  动画精讲: '通过动画演绎、过程可视化和故事化表达，把课堂中难理解、讲得快或缺少直观呈现的知识点讲清楚。',
  动画讲透知识点: '通过动画演绎、过程可视化和故事化表达，把课堂中难理解、讲得快或缺少直观呈现的知识点讲清楚。',
  课后小测: '孩子学完当前课或知识点后立即练习或小测，用结果确认是否掌握，并把错题和本节学情反馈出来。',
  学练测闭环: '孩子学完当前课或知识点后立即练习或小测，用结果确认是否掌握，并把错题和本节学情反馈出来。',
  新课标新考法预测: '围绕课标和考试改革带来的新情境、跨学科、开放探究及题型变化，拆解命题趋势、考查逻辑与应对方法。',
  新课标新考法: '围绕课标和考试改革带来的新情境、跨学科、开放探究及题型变化，拆解命题趋势、考查逻辑与应对方法。',
  专项培优: '根据学科高频考点、重难点、薄弱题型和考试阶段，提供专项训练、系统讲解、考前重点梳理及高频易错题训练。',
  分学科重难点专项培优: '根据学科高频考点、重难点、薄弱题型和考试阶段，提供专项训练、系统讲解、考前重点梳理及高频易错题训练。',
  举一反三: '先讲清知识与题型背后的底层原理、命题逻辑和解题路径，再通过变式题和同类题训练迁移能力。',
  '理解原理，举一反三': '先讲清知识与题型背后的底层原理、命题逻辑和解题路径，再通过变式题和同类题训练迁移能力。',
  专家规划: '由具备命题研究、教材编写或学科教研背景的专家参与课程体系、知识顺序和能力进阶路径设计。',
  命题专家与教材编者设计: '由具备命题研究、教材编写或学科教研背景的专家参与课程体系、知识顺序和能力进阶路径设计。',
  学段衔接: '从小学到高中连续覆盖课程，并针对幼小、小升初、初升高等学习跃迁提供过渡内容，兼顾同步和拔高。',
  小初高一体化与学段衔接: '从小学到高中连续覆盖课程，并针对幼小、小升初、初升高等学习跃迁提供过渡内容，兼顾同步和拔高。',
  万能解法: '讲解知识和问题背后的底层原理、通用方法与学科思维，帮助孩子从固定套路转向自主分析与迁移。',
  底层方法与思维培养: '讲解知识和问题背后的底层原理、通用方法与学科思维，帮助孩子从固定套路转向自主分析与迁移。',
  AI定制学习方案: '根据学生当前条件、目标和可投入时间，自动生成个人学习路径、每日任务、课程顺序和阶段进度。',
  'AI 量身定制学习方案': '根据学生当前条件、目标和可投入时间，自动生成个人学习路径、每日任务、课程顺序和阶段进度。',
  AI私教答疑: '在学习过程中支持文字、语音或图片等输入，围绕当前知识问题进行即时互动答疑和追问澄清。',
  'AI 私教随时答疑': '在学习过程中支持文字、语音或图片等输入，围绕当前知识问题进行即时互动答疑和追问澄清。',
  AI拍题精学: '识别拍摄的具体题目后，通过分步提问、条件梳理和思路提示引导孩子自主推导，而不是直接展示最终答案。',
  'AI 拍题精学': '识别拍摄的具体题目后，通过分步提问、条件梳理和思路提示引导孩子自主推导，而不是直接展示最终答案。',
  极速预习复习: '课前拍摄课本或学习内容快速获得知识梳理，课后拍摄笔记或内容快速回顾当天重点和薄弱处。',
  AI错题本: '把线下错题拍照上传并整理到线上错题本，便于学生随时查阅、复盘，并围绕同类题继续训练。',
  'AI 错题本': '把线下错题拍照上传并整理到线上错题本，便于学生随时查阅、复盘，并围绕同类题继续训练。',
  真人老师督学: '由专属真人伴学老师持续参与学习管理，进行问题诊断、阶段计划、提醒督促、回访复盘和家长同步。',
  学情报告反馈: '按日或按周汇总学习内容、时长、行为和效果，通过家长可访问的报告反馈真实进度、薄弱点与异常情况。',
};

export default SemanticSearchResult;
