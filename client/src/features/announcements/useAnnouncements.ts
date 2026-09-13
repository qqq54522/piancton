import { useQuery } from '@tanstack/react-query';

import { fetchAnnouncementUnreadCount } from '@client/src/api/announcements';

export const announcementKeys = {
  all: ['announcements'] as const,
  feed: ['announcements', 'feed'] as const,
  unread: ['announcements', 'unread-count'] as const,
  manage: ['announcements', 'manage'] as const,
};

export function useAnnouncementUnreadCount(enabled: boolean) {
  return useQuery({
    queryKey: announcementKeys.unread,
    queryFn: fetchAnnouncementUnreadCount,
    enabled,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
    staleTime: 15_000,
  });
}
