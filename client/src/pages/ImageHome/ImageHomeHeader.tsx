import { Link } from 'react-router-dom';
import { FileClock, Upload } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { CanRole } from '@client/src/lib/auth';

const ImageHomeHeader = ({
  isDesigner,
  onOpenUpload,
}: {
  isDesigner: boolean;
  onOpenUpload: () => void;
}) => (
  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">图片库</h1>
      <p className="mt-1 text-sm text-muted-foreground">统一搜索素材，业务关系在素材详情中维护</p>
    </div>
    {isDesigner && (
      <div className="flex items-center gap-2">
        <CanRole roles={['designer']}>
          <Button variant="outline" size="sm" asChild>
            <Link to="/trash"><FileClock className="mr-1.5 size-4" />回收站</Link>
          </Button>
          <Button size="sm" onClick={onOpenUpload}>
            <Upload className="mr-1.5 size-4" />上传主图
          </Button>
        </CanRole>
      </div>
    )}
  </div>
);

export default ImageHomeHeader;
