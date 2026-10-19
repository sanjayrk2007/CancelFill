import { useState, useEffect, useCallback, useRef } from 'react';
import { NotificationsContext } from './NotificationsContextDef';
import client from '../api/client';
import { useAuth } from './useAuth';

const POLL_INTERVAL_MS = 10000;
const BUSINESS_CANCELLATION_TYPE = 'BOOKING_CANCELLED_BY_BUSINESS';

export function NotificationsProvider({ children }) {
  const { user, role } = useAuth();
  const userId = user?.id ?? null;

  const [unreadCount, setUnreadCount] = useState(0);
  const [cancellationAlerts, setCancellationAlerts] = useState([]);
  const dismissedRef = useRef(new Set());

  const refresh = useCallback(async () => {
    if (!userId) return;
    try {
      const response = await client.get('/api/v1/notifications', {
        params: { unread_only: true, limit: 50 },
      });
      const items = response.data?.items || [];
      setUnreadCount(response.data?.unread_count ?? 0);
      if (role === 'CUSTOMER') {
        setCancellationAlerts(
          items.filter(
            (n) => n.type === BUSINESS_CANCELLATION_TYPE && !dismissedRef.current.has(n.id)
          )
        );
      }
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    }
  }, [userId, role]);

  useEffect(() => {
    dismissedRef.current = new Set();
    if (!userId) return undefined;

    refresh();
    const intervalId = setInterval(refresh, POLL_INTERVAL_MS);
    const onVisible = () => {
      if (document.visibilityState === 'visible') refresh();
    };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', refresh);

    return () => {
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', refresh);
    };
  }, [userId, refresh]);

  const dismissCancellationAlert = useCallback(
    async (notificationId) => {
      dismissedRef.current.add(notificationId);
      setCancellationAlerts((prev) => prev.filter((n) => n.id !== notificationId));
      try {
        await client.post(`/api/v1/notifications/${notificationId}/read`);
      } catch (err) {
        console.error('Failed to mark notification read:', err);
      }
      refresh();
    },
    [refresh]
  );

  const value = {
    unreadCount: userId ? unreadCount : 0,
    cancellationAlerts: userId && role === 'CUSTOMER' ? cancellationAlerts : [],
    refresh,
    dismissCancellationAlert,
  };

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

export { NotificationsContext };
export default NotificationsProvider;
