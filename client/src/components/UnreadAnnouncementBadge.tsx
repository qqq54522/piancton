interface UnreadAnnouncementBadgeProps {
  count: number;
  className?: string;
}

export default function UnreadAnnouncementBadge({
  count,
  className = '',
}: UnreadAnnouncementBadgeProps) {
  if (count <= 0) return null;
  const label = count > 99 ? '99+' : String(count);

  return (
    <span
      aria-label={`${count} 条未读消息`}
      className={`pointer-events-none absolute -bottom-0.5 -right-0.5 z-10 grid min-h-5 min-w-5 place-items-center rounded-full border-2 border-white bg-red-500 px-1 text-[10px] font-bold leading-none text-white shadow-sm ${className}`}
    >
      {label}
    </span>
  );
}
