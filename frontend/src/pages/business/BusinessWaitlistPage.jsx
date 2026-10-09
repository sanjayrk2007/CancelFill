import { useState, useEffect, useCallback, useMemo } from 'react';
import client from '../../api/client';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import EmptyState from '../../components/ui/EmptyState';
import { SkeletonTable } from '../../components/ui/Skeleton';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table';
import { formatLocalDateTime } from '../../lib/formatters';
import { Users, RotateCw, AlertCircle, Search } from 'lucide-react';

export default function BusinessWaitlistPage() {
  useDocumentTitle('Business Waitlists');

  const [waitlistSlots, setWaitlistSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'WAITING' | 'OFFERED'
  const [searchQuery, setSearchQuery] = useState('');

  const fetchWaitlist = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setLoading(true);
    }
    setError(null);
    try {
      const response = await client.get('/api/v1/business/waitlist');
      setWaitlistSlots(response.data || []);
    } catch (err) {
      console.error('Error fetching business waitlist:', err);
      setError(err.response?.data?.detail || 'Failed to load business waitlist.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWaitlist(false);
  }, [fetchWaitlist]);

  // Flatten entries across all slots
  const allEntries = useMemo(() => {
    const list = [];
    waitlistSlots.forEach((slot) => {
      (slot.entries || []).forEach((entry) => {
        list.push({
          ...entry,
          resource_id: slot.resource_id,
          slot_id: slot.slot_id,
        });
      });
    });
    return list;
  }, [waitlistSlots]);

  // Apply status and search filter
  const filteredEntries = useMemo(() => {
    return allEntries.filter((item) => {
      if (filter === 'WAITING' && item.status !== 'WAITING') return false;
      if (filter === 'OFFERED' && item.status !== 'OFFERED') return false;

      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesUser = item.user_name?.toLowerCase().includes(query);
        const matchesResource = item.resource_id?.toLowerCase().includes(query);
        if (!matchesUser && !matchesResource) return false;
      }

      return true;
    });
  }, [allEntries, filter, searchQuery]);

  const waitingCount = useMemo(() => allEntries.filter((e) => e.status === 'WAITING').length, [allEntries]);
  const offeredCount = useMemo(() => allEntries.filter((e) => e.status === 'OFFERED').length, [allEntries]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900">
            Waitlist Queues
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Inspect ordered waitlist queues and candidates across your published slots.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchWaitlist(true)}
            icon={RotateCw}
            disabled={loading}
            aria-label="Refresh waitlists"
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Inline Error State with Retry */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span className="text-xs font-medium">{error}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={() => fetchWaitlist(true)}>
            Retry
          </Button>
        </div>
      )}

      {/* Filter Chips & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 p-1 bg-zinc-100 rounded-lg border border-zinc-200/60 w-fit">
          <button
            type="button"
            onClick={() => setFilter('ALL')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
              filter === 'ALL'
                ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            All ({allEntries.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('WAITING')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
              filter === 'WAITING'
                ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            Waiting ({waitingCount})
          </button>
          <button
            type="button"
            onClick={() => setFilter('OFFERED')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
              filter === 'OFFERED'
                ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            Offered ({offeredCount})
          </button>
        </div>

        <div className="relative sm:w-64">
          <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search candidate or slot..."
            className="w-full bg-white border border-zinc-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
            aria-label="Search waitlist candidates"
          />
        </div>
      </div>

      {/* Linear-Style Table */}
      {loading ? (
        <SkeletonTable rows={5} cols={5} />
      ) : filteredEntries.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No waitlist candidates"
          description={
            searchQuery
              ? `No waitlist entries matching "${searchQuery}".`
              : filter !== 'ALL'
              ? `No entries with status "${filter.toLowerCase()}".`
              : 'There are currently no active waitlist candidates registered for your slots.'
          }
          action={
            searchQuery || filter !== 'ALL' ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setFilter('ALL');
                  setSearchQuery('');
                }}
              >
                Clear filters
              </Button>
            ) : null
          }
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow hover={false}>
              <TableHead>Queue Position</TableHead>
              <TableHead>Candidate Name</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Joined Time</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEntries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell>
                  <span className="font-semibold text-zinc-900 font-mono">
                    #{entry.position || 1}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="font-medium text-zinc-900">
                    {entry.user_name || 'Customer Candidate'}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex flex-col">
                    <span className="text-zinc-900 font-medium">{entry.resource_id}</span>
                    <span className="text-[11px] text-zinc-400 font-mono">{entry.slot_id}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge status={entry.status} size="sm" />
                </TableCell>
                <TableCell>
                  <span className="text-zinc-600 text-xs">
                    {formatLocalDateTime(entry.joined_at)}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
