export interface UploadBatchProgress {
  completed: number;
  currentFile: File;
  total: number;
}

export interface UploadBatchSuccess<T> {
  file: File;
  value: T;
}

export interface UploadBatchFailure {
  error: unknown;
  file: File;
}

export interface UploadBatchResult<T> {
  failures: UploadBatchFailure[];
  successes: UploadBatchSuccess<T>[];
}

export function mergeUploadFiles(current: File[], incoming: File[]): File[] {
  const seen = new Set(current.map(uploadFileKey));
  const merged = [...current];
  incoming.forEach((file) => {
    const key = uploadFileKey(file);
    if (seen.has(key)) return;
    seen.add(key);
    merged.push(file);
  });
  return merged;
}

export function titleForUpload(file: File, index: number, total: number, singleTitle: string): string {
  if (total === 1 && singleTitle.trim()) return singleTitle.trim();
  return file.name.replace(/\.[^.]+$/, '') || `图片 ${index + 1}`;
}

export async function runUploadBatch<T>(
  files: File[],
  uploadOne: (file: File, index: number) => Promise<T>,
  onProgress?: (progress: UploadBatchProgress) => void,
): Promise<UploadBatchResult<T>> {
  const successes: UploadBatchSuccess<T>[] = [];
  const failures: UploadBatchFailure[] = [];

  for (const [index, file] of files.entries()) {
    onProgress?.({ completed: index, currentFile: file, total: files.length });
    try {
      successes.push({ file, value: await uploadOne(file, index) });
    } catch (error) {
      failures.push({ error, file });
    }
  }

  return { failures, successes };
}

function uploadFileKey(file: File): string {
  return `${file.name}\u0000${file.size}\u0000${file.lastModified}`;
}
