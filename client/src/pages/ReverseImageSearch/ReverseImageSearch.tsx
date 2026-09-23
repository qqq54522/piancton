import { useEffect, useState } from 'react';
import { Loader2, ScanSearch, Upload } from 'lucide-react';
import { Link } from 'react-router-dom';

import * as imageApi from '@client/src/api/image';
import { getApiError } from '@client/src/api/client';
import PageHeader from '@client/src/components/PageHeader';
import { Button } from '@client/src/components/ui/button';

const MAX_BYTES = 10 * 1024 * 1024;

export default function ReverseImageSearch() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [result, setResult] = useState<imageApi.ReverseImageSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const chooseFile = (next: File | undefined) => {
    if (!next) return;
    if (!next.type.startsWith('image/')) {
      setError('请选择图片文件');
      return;
    }
    if (next.size > MAX_BYTES) {
      setError('图片不能超过 10MB');
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(next);
    setPreviewUrl(URL.createObjectURL(next));
    setResult(null);
    setError('');
  };

  const search = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      setResult(await imageApi.reverseImageSearch(file));
    } catch (requestError) {
      setError(getApiError(requestError).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-shell max-w-[1400px]">
      <PageHeader
        title="以图查图"
        description="上传一张图片，在卖点图片素材中查找相同或视觉上相似的图片。查询图不会进入素材库。"
      />

      <section className="surface-card mt-7 p-5 sm:p-7">
        <label
          htmlFor="reverse-image-file"
          className="flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-secondary/30 px-5 text-center transition hover:border-foreground/30 hover:bg-secondary/50"
        >
          {previewUrl ? (
            <img src={previewUrl} alt="待查图片预览" className="max-h-48 max-w-full rounded-xl object-contain" />
          ) : (
            <>
              <span className="grid size-12 place-items-center rounded-2xl bg-white shadow-sm">
                <Upload className="size-5 text-muted-foreground" />
              </span>
              <span className="mt-3 text-sm font-medium">点击选择或拖入一张图片</span>
              <span className="mt-1 text-xs text-muted-foreground">支持常见图片格式，最大 10MB</span>
            </>
          )}
          <input
            id="reverse-image-file"
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="sr-only"
            onChange={(event) => chooseFile(event.target.files?.[0])}
          />
        </label>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button type="button" disabled={!file || loading} onClick={search}>
            {loading ? <Loader2 className="size-4 animate-spin" /> : <ScanSearch className="size-4" />}
            {loading ? '正在查找…' : '开始查找'}
          </Button>
          {file && <span className="text-xs text-muted-foreground">{file.name}</span>}
        </div>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </section>

      {result && (
        <section className="mt-7">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">检索结果</h2>
              <p className="mt-1 text-sm text-muted-foreground">{result.message}</p>
            </div>
          </div>
          {result.matches.length ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {result.matches.map((match) => (
                <Link key={match.imageId} to={match.detailUrl} className="surface-card overflow-hidden transition hover:-translate-y-0.5 hover:shadow-md">
                  <div className="aspect-[4/3] bg-secondary/40">
                    <img src={match.thumbnailUrl} alt={match.title} className="size-full object-contain" />
                  </div>
                  <div className="p-3">
                    <p className="truncate text-sm font-medium">{match.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {match.matchType === 'same_or_transformed' ? '可能是同一张图片' : '视觉上相似'} · {Math.round(match.score * 100)}%
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="surface-card flex min-h-32 items-center justify-center p-6 text-sm text-muted-foreground">
              暂未找到匹配图片
            </div>
          )}
        </section>
      )}
    </div>
  );
}
