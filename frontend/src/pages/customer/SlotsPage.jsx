import { useState, useEffect, useCallback, useMemo } from 'react';
import client from '../../api/client';
import { useToast } from '../../context/useToast';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import Card from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import EmptyState from '../../components/ui/EmptyState';
import { SkeletonCard } from '../../components/ui/Skeleton';
import { formatLocalTimeRange, formatCurrency } from '../../lib/formatters';
import {
  CalendarDays,
  Clock,
  RotateCw,
  AlertCircle,
  Search,
  Check,
  UserPlus,
} from 'lucide-react';

export default function SlotsPage() {
  useDocumentTitle('Appointment Slots');

  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'AVAILABLE' | 'WAITLIST'
  const [searchQuery, setSearchQuery] = useState('');
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const { success, error: toastError } = useToast();

  const fetchSlots = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setLoading(true);
    }
    setError(null);
    try {
      const response = await client.get('/api/v1/slots');
      setSlots(response.data || []);
    } catch (err) {
      console.error('Error fetching slots:', err);
      setError(err.response?.data?.detail || 'Failed to load slots. Please check your connection.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSlots(false);
  }, [fetchSlots]);

  const handleBookNow = async (slot) => {
    setActionLoadingId(slot.id);
    try {
      await client.post('/api/v1/bookings', { slot_id: slot.id });
      success(`Booked slot for ${slot.resource_id}.`);
      await fetchSlots(true);
    } catch (err) {
      const message = err.response?.data?.detail || 'Failed to book slot.';
      toastError(message);
      await fetchSlots(true);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleJoinWaitlist = async (slot) => {
    setActionLoadingId(slot.id);
    try {
      await client.post('/api/v1/waitlist', { slot_id: slot.id });
      success(`Joined waitlist for ${slot.resource_id}.`);
      await fetchSlots(true);
    } catch (err) {
      const message = err.response?.data?.detail || 'Failed to join waitlist.';
      toastError(message);
      await fetchSlots(true);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Filter slots by status filter and search query
  const filteredSlots = useMemo(() => {
    return slots.filter((slot) => {
      // Filter chip condition
      if (filter === 'AVAILABLE' && slot.status !== 'AVAILABLE') return false;
      if (filter === 'WAITLIST' && slot.status !== 'BOOKED' && slot.status !== 'HELD') return false;

      // Search query condition
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesResource = slot.resource_id?.toLowerCase().includes(query);
        const matchesId = slot.id?.toLowerCase().includes(query);
        if (!matchesResource && !matchesId) return false;
      }

      return true;
    });
  }, [slots, filter, searchQuery]);

  // Group filtered slots by local day (e.g. "Thu 10 Oct 2026")
  const groupedSlots = useMemo(() => {
    const groups = {};
    filteredSlots.forEach((slot) => {
      const dateObj = new Date(slot.start_time);
      const dayKey = isNaN(dateObj.getTime())
        ? 'Upcoming Slots'
        : new Intl.DateTimeFormat('en-US', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric',
          }).format(dateObj);

      if (!groups[dayKey]) {
        groups[dayKey] = [];
      }
      groups[dayKey].push(slot);
    });
    return groups;
  }, [filteredSlots]);

  const availableCount = useMemo(() => slots.filter((s) => s.status === 'AVAILABLE').length, [slots]);
  const waitlistCount = useMemo(() => slots.filter((s) => s.status === 'BOOKED' || s.status === 'HELD').length, [slots]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900">
            Appointment Slots
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Browse schedule openings to book immediately or join priority waitlists.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchSlots(true)}
            icon={RotateCw}
            disabled={loading}
            aria-label="Refresh slots"
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
          <Button variant="secondary" size="sm" onClick={() => fetchSlots(true)}>
            Retry
          </Button>
        </div>
      )}

      {/* Filter Chips & Search Box */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Filter Chips */}
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
            All ({slots.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('AVAILABLE')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
              filter === 'AVAILABLE'
                ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            Available ({availableCount})
          </button>
          <button
            type="button"
            onClick={() => setFilter('WAITLIST')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
              filter === 'WAITLIST'
                ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            Waitlist ({waitlistCount})
          </button>
        </div>

        {/* Search Box */}
        <div className="relative sm:w-64">
          <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by resource..."
            className="w-full bg-white border border-zinc-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
            aria-label="Search appointment slots"
          />
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <SkeletonCard count={6} />
      ) : Object.keys(groupedSlots).length === 0 ? (
        <EmptyState
          icon={CalendarDays}
          title="No slots found"
          description={
            searchQuery
              ? `No appointment slots matching "${searchQuery}".`
              : filter !== 'ALL'
              ? `No slots matching filter "${filter.toLowerCase()}".`
              : 'There are currently no slots published in the system.'
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
            ) : (
              <Button variant="secondary" size="sm" onClick={() => fetchSlots(true)}>
                Check again
              </Button>
            )
          }
        />
      ) : (
        /* Slots Grouped by Day */
        <div className="space-y-8">
          {Object.entries(groupedSlots).map(([dayLabel, daySlots]) => (
            <section key={dayLabel} className="space-y-3">
              {/* Day Header */}
              <div className="flex items-center justify-between pb-2 border-b border-zinc-100">
                <div className="flex items-center gap-2">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                    {dayLabel}
                  </h2>
                  <span className="text-[11px] font-medium text-zinc-400">
                    ({daySlots.length} {daySlots.length === 1 ? 'slot' : 'slots'})
                  </span>
                </div>
              </div>

              {/* Cards Grid: Cal.com / Calendly clean booking card feel */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {daySlots.map((slot) => {
                  const isAvailable = slot.status === 'AVAILABLE';
                  const isBookedOrHeld = slot.status === 'BOOKED' || slot.status === 'HELD';
                  const isProcessing = actionLoadingId === slot.id;

                  return (
                    <Card
                      key={slot.id}
                      hover
                      className="flex flex-col justify-between"
                    >
                      <div>
                        {/* Resource & Badge */}
                        <div className="flex items-start justify-between gap-2 pb-3 mb-3 border-b border-zinc-100">
                          <div>
                            <h3 className="text-sm font-semibold text-zinc-900 tracking-tight">
                              {slot.resource_id}
                            </h3>
                            <span className="text-[11px] font-mono text-zinc-400">
                              {slot.id}
                            </span>
                          </div>
                          <Badge status={slot.status} size="sm" />
                        </div>

                        {/* Time & Price */}
                        <div className="space-y-2 text-xs">
                          <div className="flex items-center gap-2 text-zinc-700 font-medium">
                            <Clock className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                            <span>
                              {formatLocalTimeRange(slot.start_time, slot.end_time)}
                            </span>
                          </div>

                          <div className="flex items-center justify-between pt-1">
                            <span className="text-[11px] text-zinc-500">Session fee</span>
                            <span className="font-semibold text-zinc-900">
                              {formatCurrency(slot.price)}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Primary Action Button */}
                      <div className="mt-4 pt-3 border-t border-zinc-100">
                        {isAvailable ? (
                          <Button
                            variant="primary"
                            size="sm"
                            className="w-full"
                            icon={Check}
                            isLoading={isProcessing}
                            disabled={isProcessing}
                            onClick={() => handleBookNow(slot)}
                          >
                            Book slot
                          </Button>
                        ) : isBookedOrHeld ? (
                          <Button
                            variant="secondary"
                            size="sm"
                            className="w-full"
                            icon={UserPlus}
                            isLoading={isProcessing}
                            disabled={isProcessing}
                            onClick={() => handleJoinWaitlist(slot)}
                          >
                            Join waitlist
                          </Button>
                        ) : (
                          <Button
                            variant="secondary"
                            size="sm"
                            className="w-full"
                            disabled
                          >
                            Unavailable
                          </Button>
                        )}
                      </div>
                    </Card>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
