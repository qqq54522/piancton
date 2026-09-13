import { api } from './client';

export interface Announcement {
  id: string;
  title: string;
  content: string;
  publisherName: string;
  publishedAt: string;
}

export interface AnnouncementListResponse {
  items: Announcement[];
}

export interface AnnouncementFeedResponse extends AnnouncementListResponse {
  unreadCount: number;
}

export interface AnnouncementUnreadCount {
  unreadCount: number;
}

export async function fetchAnnouncements(): Promise<AnnouncementFeedResponse> {
  return (await api.get('/api/announcements')).data;
}

export async function fetchAnnouncementUnreadCount(): Promise<AnnouncementUnreadCount> {
  return (await api.get('/api/announcements/unread-count')).data;
}

export async function markAnnouncementsRead(
  throughPublishedAt: string,
): Promise<AnnouncementUnreadCount> {
  return (
    await api.post('/api/announcements/read', { throughPublishedAt })
  ).data;
}

export async function fetchManagedAnnouncements(): Promise<AnnouncementListResponse> {
  return (await api.get('/api/admin/announcements')).data;
}

export async function publishAnnouncement(payload: {
  title: string;
  content: string;
}): Promise<Announcement> {
  return (await api.post('/api/admin/announcements', payload)).data;
}
