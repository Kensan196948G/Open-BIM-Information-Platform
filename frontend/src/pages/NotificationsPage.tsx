import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { Bell, CheckCheck } from "lucide-react";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/api/notifications";
import { fmtDate } from "@/lib/fmt";

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => listNotifications({ size: 100 }),
  });

  const readMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const readAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const items = data?.items ?? [];

  return (
    <div className="mx-auto max-w-[980px] p-5 sm:p-6">
      <div className="mb-5 flex items-end justify-between gap-3">
        <div>
          <h1 className="t-display">通知</h1>
          <p className="t-sec mt-1">
            承認依頼・承認結果・状態変更（未読 {data?.unread_count ?? 0} 件）
          </p>
        </div>
        <button
          className="app-btn app-btn-sm"
          disabled={readAllMutation.isPending || (data?.unread_count ?? 0) === 0}
          onClick={() => readAllMutation.mutate()}
        >
          <CheckCheck className="h-3.5 w-3.5" />
          すべて既読
        </button>
      </div>

      {isLoading ? (
        <div className="p-6 t-sec">読み込み中...</div>
      ) : items.length === 0 ? (
        <div className="app-card-pad py-16 text-center">
          <Bell className="mx-auto mb-3 h-10 w-10" style={{ color: "var(--text-3)" }} />
          <div className="t-h2">通知はありません</div>
          <div className="t-sec mt-1">承認依頼や状態変更があるとここに表示されます。</div>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((notification) => (
            <div
              key={notification.id}
              className="app-card flex items-start gap-3 p-4"
              style={{
                opacity: notification.is_read ? 0.65 : 1,
                borderColor: notification.is_read
                  ? "var(--border)"
                  : "var(--primary-border)",
              }}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-semibold" style={{ color: "var(--text)" }}>
                    {notification.title}
                  </span>
                  {!notification.is_read && (
                    <span className="h-2 w-2 rounded-full bg-[var(--primary)]" />
                  )}
                </div>
                {notification.body && (
                  <p className="t-sec mt-1 text-xs">{notification.body}</p>
                )}
                <div className="t-tiny mt-2">{fmtDate(notification.created_at, true)}</div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {notification.link && (
                  <Link className="app-btn app-btn-ghost app-btn-sm" to={notification.link}>
                    開く
                  </Link>
                )}
                {!notification.is_read && (
                  <button
                    className="app-btn app-btn-ghost app-btn-sm"
                    onClick={() => readMutation.mutate(notification.id)}
                  >
                    既読にする
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
