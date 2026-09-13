// @vitest-environment jsdom

import { describe, expect, it, vi } from 'vitest';

import { mergeUploadFiles, runUploadBatch, titleForUpload } from './uploadBatch';

function imageFile(name: string, content = name, lastModified = 1) {
  return new File([content], name, { lastModified, type: 'image/png' });
}

describe('uploadBatch', () => {
  it('keeps existing files and ignores the same file when users add another selection', () => {
    const first = imageFile('第一张.png');
    const second = imageFile('第二张.png');

    expect(mergeUploadFiles([first], [first, second])).toEqual([first, second]);
  });

  it('uses the edited title only for a single upload and file names for a batch', () => {
    const file = imageFile('新疆合作案例.png');

    expect(titleForUpload(file, 0, 1, '自定义名称')).toBe('自定义名称');
    expect(titleForUpload(file, 0, 2, '不会共用的名称')).toBe('新疆合作案例');
  });

  it('continues after one file fails and reports progress without retrying successful files', async () => {
    const first = imageFile('成功.png');
    const second = imageFile('失败.png');
    const third = imageFile('继续.png');
    const progress = vi.fn();
    const uploadOne = vi.fn(async (file: File) => {
      if (file === second) throw new Error('network');
      return file.name;
    });

    const result = await runUploadBatch([first, second, third], uploadOne, progress);

    expect(result.successes.map(({ file }) => file)).toEqual([first, third]);
    expect(result.failures.map(({ file }) => file)).toEqual([second]);
    expect(uploadOne).toHaveBeenCalledTimes(3);
    expect(progress).toHaveBeenLastCalledWith({ completed: 2, currentFile: third, total: 3 });
  });
});
