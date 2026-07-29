export interface ChannelRecommendation {
  value: string;
  description: string;
}

export const CHANNEL_RECOMMENDATIONS: ChannelRecommendation[] = [
  {
    value: 'PPT',
    description: '适合销售讲解和内部汇报，优先使用结构清楚、信息层级完整、能承接讲解节奏的素材。',
  },
  {
    value: '品牌手册',
    description: '适合沉淀品牌与产品标准表达，优先使用口径稳定、视觉规范、证明关系清晰的素材。',
  },
  {
    value: '手机端大图',
    description: '适合移动端首屏或重点位置，优先使用主体突出、标题直接、能在短时间建立卖点认知的素材。',
  },
  {
    value: '手机端小图',
    description: '手机屏幕较小，用户识别内容的有效时间很短，建议优先使用重点明确、文字更少、主体更集中的素材。',
  },
  {
    value: '官网大图',
    description: '适合官网核心展示区域，优先使用视觉完成度高、卖点明确、能承担品牌信任感的素材。',
  },
  {
    value: '官网小图',
    description: '适合官网列表、模块入口或辅助说明，优先使用信息单点清楚、缩小后仍容易识别的素材。',
  },
];

export const CHANNEL_VALUES = CHANNEL_RECOMMENDATIONS.map((item) => item.value);

export function channelRecommendationFor(channel: string): ChannelRecommendation | undefined {
  return CHANNEL_RECOMMENDATIONS.find((item) => item.value === channel);
}
