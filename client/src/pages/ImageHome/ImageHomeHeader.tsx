import { Link } from 'react-router-dom';
import { FileClock, SlidersHorizontal, Tags, Upload } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { CanRole } from '@client/src/lib/auth';

interface ImageHomeHeaderProps {
  pageTitle: string;
  isRoot: boolean;
  isDesigner: boolean;
  onOpenFilter: () => void;
  onOpenTagPanel: () => void;
  onOpenUpload: () => void;
}

const ImageHomeHeader = ({
  pageTitle,
  isRoot,
  isDesigner,
  onOpenFilter,
  onOpenTagPanel,
  onOpenUpload,
}: ImageHomeHeaderProps) => (
  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
    <h1 className="text-2xl font-semibold tracking-tight text-foreground">
      {pageTitle}
    </h1>
    <div className="flex items-center gap-2">
      {isRoot && !isDesigner && (
        <Button variant="outline" size="sm" onClick={onOpenFilter}>
          <SlidersHorizontal className="mr-1.5 size-4" />
          精确查找
        </Button>
      )}
      <CanRole roles={['designer']}>
        {isRoot && (
          <Button variant="outline" size="sm" asChild>
            <Link to="/trash">
              <FileClock className="mr-1.5 size-4" />
              回收站
            </Link>
          </Button>
        )}
      </CanRole>
      <CanRole roles={['designer']}>
        {isRoot && (
          <Button variant="outline" size="sm" onClick={onOpenTagPanel}>
            <Tags className="mr-1.5 size-4" />
            标签管理
          </Button>
        )}
      </CanRole>
      <CanRole roles={['designer']}>
        {isRoot && (
          <Button size="sm" onClick={onOpenUpload}>
            <Upload className="mr-1.5 size-4" />
            上传图片
          </Button>
        )}
      </CanRole>
    </div>
  </div>
);

export default ImageHomeHeader;
