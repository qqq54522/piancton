import { Link } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

interface BreadcrumbItem {
  id: string | null;
  name: string;
}

interface ImageBreadcrumbProps {
  items: BreadcrumbItem[];
}

const ImageBreadcrumb = ({ items }: ImageBreadcrumbProps) => (
  <nav className="mt-4 flex flex-wrap items-center gap-1 text-sm">
    {items.map((item, index) => (
      <span key={item.id ?? 'root'} className="flex items-center gap-1">
        {index > 0 && (
          <ChevronRight className="size-3.5 text-muted-foreground/50" />
        )}
        {index === items.length - 1 ? (
          <span className="font-medium text-foreground">{item.name}</span>
        ) : (
          <Link
            to={item.id ? `/tag/${item.id}` : '/'}
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground"
          >
            {index === 0 && <Home className="size-3.5" />}
            {item.name}
          </Link>
        )}
      </span>
    ))}
  </nav>
);

export default ImageBreadcrumb;
