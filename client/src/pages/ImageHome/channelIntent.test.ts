import { describe, expect, it } from 'vitest';

import { understandImageChannelIntent, type ChannelIntentEntry } from './channelIntent';
import { isChannelIntentInCatalog } from './channelIntentCatalog';

describe('image channel intent understanding', () => {
  it('recognizes mobile family without forcing large or small variants', () => {
    expect(understandImageChannelIntent('我想找一张手机端能够体现家长能看到学习结果的图')).toMatchObject({
      channelFamily: 'mobile',
      channelSize: 'unspecified',
      exactChannel: null,
      candidateChannels: ['手机端大图', '手机端小图'],
      scenePreference: 'scene',
      confidence: 'high',
    });
  });

  it('recognizes mobile small image language when the query names a compact placement', () => {
    expect(understandImageChannelIntent('找一个手机端列表入口小图，能表达 AI 错题本')).toMatchObject({
      channelFamily: 'mobile',
      channelSize: 'small',
      exactChannel: '手机端小图',
      candidateChannels: ['手机端小图'],
    });
  });

  it('recognizes operation long-image module language as mobile placements', () => {
    expect(understandImageChannelIntent('运营长图里用的拍题精学')).toMatchObject({
      channelFamily: 'mobile',
      channelSize: 'unspecified',
      exactChannel: null,
      candidateChannels: ['手机端大图', '手机端小图'],
    });
    expect(understandImageChannelIntent('运营长图大模块里用的拍题精学')).toMatchObject({
      channelFamily: 'mobile',
      channelSize: 'large',
      exactChannel: '手机端大图',
      candidateChannels: ['手机端大图'],
    });
    expect(understandImageChannelIntent('运营长图小模块里用的拍题精学')).toMatchObject({
      channelFamily: 'mobile',
      channelSize: 'small',
      exactChannel: '手机端小图',
      candidateChannels: ['手机端小图'],
    });
  });

  it('recognizes function image wording as non-scene preference', () => {
    expect(understandImageChannelIntent('手机端用的拍题精学功能图')).toMatchObject({
      channelFamily: 'mobile',
      scenePreference: 'non_scene',
    });
  });

  it('uses mobile defaults for explicit scene or function image requests without channel words', () => {
    expect(understandImageChannelIntent('拍题精学场景图')).toMatchObject({
      channelFamily: 'mobile',
      channelSize: 'unspecified',
      exactChannel: null,
      candidateChannels: ['手机端大图', '手机端小图'],
      scenePreference: 'scene',
    });
    expect(understandImageChannelIntent('拍题精学功能图')).toMatchObject({
      channelFamily: 'mobile',
      channelSize: 'unspecified',
      exactChannel: null,
      candidateChannels: ['手机端大图', '手机端小图'],
      scenePreference: 'non_scene',
    });
  });

  it('recognizes website hero language as website large image', () => {
    expect(understandImageChannelIntent('官网首页首屏想放一张学习报告反馈主视觉')).toMatchObject({
      channelFamily: 'website',
      channelSize: 'large',
      exactChannel: '官网大图',
      candidateChannels: ['官网大图'],
    });
  });

  it('recognizes PPT and brand manual as direct channels', () => {
    expect(understandImageChannelIntent('我想找一张能在 PPT 用的拍题精学')).toMatchObject({
      channelFamily: 'ppt',
      exactChannel: 'PPT',
      candidateChannels: ['PPT'],
    });
    expect(understandImageChannelIntent('要放进销售 PPT 里讲 AI 私教答疑')).toMatchObject({
      channelFamily: 'ppt',
      exactChannel: 'PPT',
      candidateChannels: ['PPT'],
    });
    expect(understandImageChannelIntent('品牌手册里需要一张能说明真人督学的素材')).toMatchObject({
      channelFamily: 'brand_manual',
      exactChannel: '品牌手册',
      candidateChannels: ['品牌手册'],
    });
  });

  it('recognizes moments posting language as mobile channel context', () => {
    expect(understandImageChannelIntent('找一张能发朋友圈的拍题精学')).toMatchObject({
      channelFamily: 'mobile',
      channelSize: 'large',
      exactChannel: '手机端大图',
      candidateChannels: ['手机端大图'],
    });
    expect(understandImageChannelIntent('找一张朋友圈九宫格入口图，表达拍题精学')).toMatchObject({
      channelFamily: 'mobile',
      channelSize: 'small',
      exactChannel: '手机端小图',
      candidateChannels: ['手机端小图'],
    });
  });

  it('does not invent channel intent without channel evidence', () => {
    expect(understandImageChannelIntent('家长看到孩子学习结果')).toBeNull();
    expect(understandImageChannelIntent('我想找一张用于测试渠道的图')).toBeNull();
  });

  it('uses managed channel phrases passed from the admin catalog', () => {
    const entries: ChannelIntentEntry[] = [
      {
        value: '家长端弹窗',
        family: 'mobile',
        size: 'small',
        phrases: ['家长端弹窗'],
      },
    ];
    expect(understandImageChannelIntent('放到家长端弹窗里看学习结果', entries)).toMatchObject({
      channelFamily: 'mobile',
      channelSize: 'small',
      exactChannel: '家长端弹窗',
      candidateChannels: ['家长端弹窗'],
      evidence: ['家长端弹窗'],
    });
  });

  it('rejects stale channel intent when the channel no longer exists in the catalog', () => {
    const staleIntent = understandImageChannelIntent('放到测试渠道里使用', [
      {
        value: '测试渠道',
        family: 'mobile',
        size: 'unspecified',
        phrases: ['测试渠道'],
      },
    ]);
    expect(isChannelIntentInCatalog(staleIntent, [])).toBe(false);
  });
});
