import { Link } from 'react-router-dom';
import { FileClock, Upload } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { CanRole } from '@client/src/lib/auth';
import { PRODUCT_NAME } from '@client/src/lib/branding';

const ImageHomeHeader = ({
  isDesigner,
  isBusiness,
  onOpenUpload,
}: {
  isDesigner: boolean;
  isBusiness: boolean;
  onOpenUpload: () => void;
}) => {
  if (isBusiness) return null;

  return (
  <header className="flex items-center justify-between gap-4">
    <div className="min-w-0">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Asset Library</p>
      <h1
        title={PRODUCT_NAME}
        className="mt-1 text-xl font-semibold tracking-normal text-foreground sm:text-2xl"
      >
        {PRODUCT_NAME}
      </h1>
    </div>
    {isDesigner ? (
      <div className="flex shrink-0 items-center gap-2">
        <CanRole roles={['designer']}>
          <Button variant="outline" size="sm" asChild>
            <Link to="/trash"><FileClock className="mr-1.5 size-4" />回收站</Link>
          </Button>
          <Button size="sm" className="bg-foreground text-background hover:bg-foreground/88" onClick={onOpenUpload}>
            <Upload className="mr-1.5 size-4" />上传主图
          </Button>
        </CanRole>
      </div>
    ) : null}
  </header>
  );
};

export default ImageHomeHeader;
