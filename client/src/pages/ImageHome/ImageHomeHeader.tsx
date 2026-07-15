import { Link } from 'react-router-dom';
import { FileClock, Upload } from 'lucide-react';

import PageHeader from '@client/src/components/PageHeader';
import { Button } from '@client/src/components/ui/button';
import { CanRole } from '@client/src/lib/auth';

const ImageHomeHeader = ({
  isDesigner,
  onOpenUpload,
}: {
  isDesigner: boolean;
  onOpenUpload: () => void;
}) => (
  <PageHeader
    eyebrow="Asset Library"
    title="业务素材库"
    description="用一句业务需求找到可用素材；上传、版本和业务关系都在同一个素材组中持续维护。"
    actions={isDesigner ? (
      <div className="flex items-center gap-2">
        <CanRole roles={['designer']}>
          <Button variant="outline" asChild>
            <Link to="/trash"><FileClock className="mr-1.5 size-4" />回收站</Link>
          </Button>
          <Button onClick={onOpenUpload}>
            <Upload className="mr-1.5 size-4" />上传主图
          </Button>
        </CanRole>
      </div>
    ) : undefined}
  />
);

export default ImageHomeHeader;
