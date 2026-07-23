// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import type {
  BusinessConcept,
  BusinessFacetCatalog,
} from '@client/src/types/api';
import { BusinessClassificationFields } from './BusinessClassificationFields';

describe('BusinessClassificationFields', () => {
  afterEach(cleanup);

  it('keeps the original source path collapsed until a green point is selected', () => {
    const concepts = [
      { id: 'concept-1', code: 'stage_transition', name: '学段衔接' },
    ] as BusinessConcept[];
    const facets: BusinessFacetCatalog = {
      proofPoints: [
        {
          code: 'pp_cultivation_stage_bridge_courses',
          conceptCode: 'stage_transition',
          name: '关键升学阶段衔接课程',
        },
      ],
      evidencePoints: [
        {
          code: 'ep_cultivation_transition_course',
          proofPointCode: 'pp_cultivation_stage_bridge_courses',
          conceptCode: 'stage_transition',
          name: '小升初和初升高过渡课程',
          sourceRef: '04-sync-cultivation.png',
          sourcePaths: [
            [
              { level: 'system', label: '同步培养体系【业务原版】' },
              { level: 'selling_point', label: '核心卖点二：小初高一体化' },
              { level: 'proof_group', label: '覆盖小学至高中毕业全学段' },
              { level: 'proof_group', label: '同步跟进 + 拔高培优' },
              { level: 'evidence_expression', label: '小升初、初升高过渡课' },
            ],
          ],
          reviewNotes: [
            '人工确认：该功能同时支持相邻卖点，不属于原图绿色路径。',
          ],
        },
      ],
    };

    const { container } = render(
      <BusinessClassificationFields
        concepts={concepts}
        facets={facets}
        conceptId="concept-1"
        proofPointCode="pp_cultivation_stage_bridge_courses"
        evidencePointCode="ep_cultivation_transition_course"
        onConceptChange={() => undefined}
        onProofPointChange={() => undefined}
        onEvidencePointChange={() => undefined}
      />,
    );

    const details = container.querySelector('details');
    expect(details?.open).toBe(false);
    fireEvent.click(screen.getByText('查看原图推导路径'));
    expect(details?.open).toBe(true);
    expect(screen.getByText('覆盖小学至高中毕业全学段')).toBeTruthy();
    expect(screen.getByText('小升初、初升高过渡课')).toBeTruthy();
    expect(screen.getByText('人工确认关系')).toBeTruthy();
    expect(
      screen.getByText('人工确认：该功能同时支持相邻卖点，不属于原图绿色路径。'),
    ).toBeTruthy();
  });
});
