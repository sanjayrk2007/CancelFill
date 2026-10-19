import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../api/client';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useNotifications } from '../context/useNotifications';
import Button from '../components/ui/Button';
import Skeleton from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';
import { formatLocalDateTime } from '../lib/formatters';
import { Bell, CheckCheck, AlertCircle } from 'lucide-react';

export default function NotificationsPage() {
  useDocumentTitle('Notifications');
  const [data, setData] = useState({ unread_count: 0, items: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { refresh: refreshUnread } = useNotifications();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.get('/api/v1/notifications');
      setData(res.data);
    } catch {
      setError('Failed to load notifications. Please try again.');
    } finally {
      setLoading(false);
    }
    refreshUnread();
  }, [refreshUnread]);

  useEffect(() => {
    load();
  }, [load]);

  const markRead = async (id) => {
    await client.post(`/api/v1/notifications/${id}/read`).catch(() => {});
    load();
  };
  const markAll = async () => {
    await client.post('/api/v1/notifications/read-all').catch(() => {});
    load();
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-zinc-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900">Notifications</h1>
          <p className="text-xs text-zinc-500 mt-1">
            Choose how you&apos;re reached (email, SMS, push) in{' '}
            <Link to="/profile" className="text-blue-600 hover:underline">
              your profile
            </Link>
            .
          </p>
        </div>
        {data.unread_count > 0 && (
          <Button variant="secondary" size="sm" icon={CheckCheck} onClick={markAll}>
            Mark all read
          </Button>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span className="text-xs font-medium">{error}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={load}>
            Retry
          </Button>
        </div>
      )}

      {loading ? (
        <div className="space-y-2.5">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-xl border border-zinc-200 bg-white p-4 space-y-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-32" />
            </div>
          ))}
        </div>
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="Nothing yet"
          description="Offers, booking changes and refunds will show up here."
          action={
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={load}>
                Refresh
              </Button>
              <Link to="/slots">
                <Button variant="primary" size="sm">
                  Browse slots
                </Button>
              </Link>
            </div>
          }
        />
      ) : (
        <ul className="space-y-2">
          {data.items.map((n) => (
            <li
              key={n.id}
              className={`rounded-xl border p-4 text-xs ${
                n.read_at ? 'bg-white border-zinc-200' : 'bg-blue-50/50 border-blue-200'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="font-semibold text-zinc-900 text-sm">{n.title}</div>
                  <p className="text-zinc-600 leading-relaxed">{n.body}</p>
                  <div className="flex items-center gap-3 text-[11px] text-zinc-400">
                    <span>{formatLocalDateTime(n.created_at)}</span>
                    {n.link && (
                      <Link to={n.link} onClick={() => !n.read_at && markRead(n.id)} className="text-blue-600 hover:underline">
                        Open
                      </Link>
                    )}
                  </div>
                </div>
                {!n.read_at && (
                  <button
                    type="button"
                    onClick={() => markRead(n.id)}
                    className="text-[11px] text-zinc-500 hover:text-zinc-900 whitespace-nowrap cursor-pointer"
                  >
                    Mark read
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
