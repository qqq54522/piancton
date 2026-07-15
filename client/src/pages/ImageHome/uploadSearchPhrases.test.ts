import { describe, expect, it } from 'vitest';

import { normalizeExpectedSearchWords } from './UploadDialog';

describe('upload search phrases', () => {
  it('trims, removes empty and duplicate phrases, and keeps at most five', () => {
    expect(normalizeExpectedSearchWords([
      ' 孩子拍题只抄答案怎么办 ',
      '',
      '整理错题太费时间',
      '孩子拍题只抄答案怎么办',
      '第三种说法',
      '第四种说法',
      '第五种说法',
      '第六种说法',
    ])).toEqual([
      '孩子拍题只抄答案怎么办',
      '整理错题太费时间',
      '第三种说法',
      '第四种说法',
      '第五种说法',
    ]);
  });
});
