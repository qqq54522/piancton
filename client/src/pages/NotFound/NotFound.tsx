import { SearchX } from 'lucide-react';
import { Link } from 'react-router-dom';

import EmptyState from '@client/src/components/EmptyState';
import { Button } from '@client/src/components/ui/button';

const NotFound = () => (
  <main className="page-shell grid min-h-[70vh] place-items-center">
    <div className="w-full max-w-xl">
      <EmptyState
        icon={<SearchX className="size-5" />}
        title="页面不存在"
        description="这个地址可能已失效，返回素材库继续搜索或管理素材。"
        action={<Button asChild><Link to="/">返回素材库</Link></Button>}
      />
    </div>
  </main>
);

export default NotFound;
