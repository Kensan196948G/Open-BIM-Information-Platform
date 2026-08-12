import { api } from "@/lib/api";

export interface AppNotification {
  id: string;
  event_type: string;
  title: string;
  body: string | null;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export async function listNotifications(params?: {
  page?: number;
  size?: number;
  unread_only?: boolean;
}): Promise<{
  items: AppNotification[];
  total: number;
  unread_count: number;
  page: number;
  size: number;
}> {
  const res = await api.get("/notifications", { params });
  return res.data;
}

export async function markNotificationRead(id: string): Promise<void> {
  await api.post(`/notifications/${id}/read`);
}

export async function markAllNotificationsRead(): Promise<void> {
  await api.post("/notifications/read-all");
}
