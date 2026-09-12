import type { ReactNode } from 'react';
import { Bot, Check, Copy, Download, FolderPlus } from 'lucide-react';

import { cn } from '@client/src/lib/utils';

interface RadialActionMenuProps {
  identityCode?: string | null;
  inProjectBasket?: boolean;
  onCopyIdentity?: () => void;
  onSendToAgent: () => void;
  onToggleProjectBasket?: () => void;
  onDownload?: () => void;
  downloadHref?: string;
  downloadLabel?: string;
  variantSelector?: ReactNode;
}

function RadialActionMenu({
  identityCode,
  inProjectBasket = false,
  onCopyIdentity,
  onSendToAgent,
  onToggleProjectBasket,
  onDownload,
  downloadHref,
  downloadLabel = '下载所选尺寸',
  variantSelector,
}: RadialActionMenuProps) {
  const actions = [
    {
      key: 'agent',
      label: '发送到 Piancton Agent',
      displayLabel: '发送到 Agent',
      icon: Bot,
      onClick: onSendToAgent,
      className: 'radial-action-menu__action--agent',
    },
    ...(onToggleProjectBasket
      ? [{
        key: 'basket',
        label: inProjectBasket ? '从项目夹移除' : '加入项目夹',
        displayLabel: inProjectBasket ? '移出项目夹' : '加入项目夹',
        icon: inProjectBasket ? Check : FolderPlus,
        onClick: onToggleProjectBasket,
        className: 'radial-action-menu__action--basket',
      }]
      : []),
    ...(identityCode && onCopyIdentity
      ? [{
        key: 'copy',
        label: `复制身份码：${identityCode}`,
        displayLabel: '复制身份码',
        icon: Copy,
        onClick: onCopyIdentity,
        className: 'radial-action-menu__action--copy',
      }]
      : []),
    ...(downloadHref
      ? [{
        key: 'download',
        label: downloadLabel,
        displayLabel: '下载',
        icon: Download,
        href: downloadHref,
        className: 'radial-action-menu__action--download',
      }]
      : []),
  ];

  return (
    <div
      className="radial-action-menu"
      aria-label="图片快捷操作"
      data-action-count={actions.length}
      onClick={(event) => event.stopPropagation()}
    >
      <span className="radial-action-menu__orbit" aria-hidden="true" />
      {actions.map((action) => {
        const Icon = action.icon;
        const commonProps = {
          type: 'button' as const,
          'aria-label': action.label,
          title: action.label,
          className: cn('radial-action-menu__action', action.className),
          onClick: (event: React.MouseEvent<HTMLButtonElement>) => {
            event.preventDefault();
            event.stopPropagation();
            action.onClick?.();
          },
        };

        if ('href' in action && action.href) {
          return (
            <a
              key={action.key}
              href={action.href}
              aria-label={action.label}
              title={action.label}
              className={cn('radial-action-menu__action', action.className)}
              onClick={(event) => {
                event.stopPropagation();
                onDownload?.();
              }}
            >
              <Icon className="size-4" />
              <span className="radial-action-menu__label">{action.displayLabel}</span>
            </a>
          );
        }

        return (
          <button key={action.key} {...commonProps}>
            <Icon className="size-4" />
            <span className="radial-action-menu__label">{action.displayLabel}</span>
          </button>
        );
      })}
      {variantSelector && (
        <div
          className="radial-action-menu__variant"
          onClick={(event) => event.stopPropagation()}
        >
          {variantSelector}
        </div>
      )}
    </div>
  );
}

export default RadialActionMenu;
