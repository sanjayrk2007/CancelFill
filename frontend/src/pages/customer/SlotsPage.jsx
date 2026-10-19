import { useState, useEffect, useCallback, useMemo } from 'react';
import client from '../../api/client';
import { useToast } from '../../context/useToast';
import { useAuth } from '../../context/useAuth';
import { checkoutAndPay } from '../../lib/payments';
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
  Check,
  UserPlus,
  Building2,
  Tag,
  Calendar,
  X,
} from 'lucide-react';

const CATEGORIES = [
  { value: 'ALL', label: 'All Categories' },
  { value: 'SALON', label: 'Salon' },
  { value: 'TUTOR', label: 'Tutor' },
  { value: 'SPORTS', label: 'Sports' },
  { value: 'CLINIC', label: 'Clinic' },
  { value: 'SERVICE_CENTER', label: 'Service Center' },
  { value: 'OTHER', label: 'Other' },
];

export default function SlotsPage() {
  useDocumentTitle('Appointment Slots');

  const [slots, setSlots] = useState([]);
  const [businesses, setBusinesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [businessId, setBusinessId] = useState('');
  const [category, setCategory] = useState('ALL');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [statusFilter, setStatusFilter] = useState('AVAILABLE');
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const { success, error: toastError } = useToast();
  const { user } = useAuth();

  const fetchBusinesses = useCallback(async () => {
    try {
      const response = await client.get('/api/v1/businesses');
      setBusinesses(response.data || []);
    } catch (err) {
      console.error('Failed to load businesses:', err);
    }
  }, []);

  const fetchSlots = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setLoading(true);
    }
    setError(null);
    try {
      const params = {};
      if (businessId) params.business_id = businessId;
      if (category && category !== 'ALL') params.category = category;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (statusFilter) params.status = statusFilter;

      const response = await client.get('/api/v1/slots', { params });
      setSlots(response.data || []);
    } catch (err) {
      console.error('Error fetching slots:', err);
      setError(err.response?.data?.detail || 'Failed to load slots. Please check your connection.');
    } finally {
      setLoading(false);
    }
  }, [businessId, category, dateFrom, dateTo, statusFilter]);

  useEffect(() => {
    fetchBusinesses();
  }, [fetchBusinesses]);

  useEffect(() => {
    fetchSlots(false);
  }, [fetchSlots]);

  const handleClearFilters = () => {
    setBusinessId('');
    setCategory('ALL');
    setDateFrom('');
    setDateTo('');
    setStatusFilter('AVAILABLE');
  };

  const hasActiveFilters = Boolean(
    businessId ||
    (category && category !== 'ALL') ||
    dateFrom ||
    dateTo ||
    statusFilter !== 'AVAILABLE'
  );

  const handleBookNow = async (slot) => {
    setActionLoadingId(slot.id);
    try {
      try {
        await client.post('/api/v1/bookings', { slot_id: slot.id });
      } catch (err) {
        if (err.response?.status !== 402) throw err;
        await checkoutAndPay({ slotId: slot.id, user });
      }
      success(`Booked slot for ${slot.resource_id}.`);
      await fetchSlots(true);
    } catch (err) {
      if (err.cancelled) {
        toastError('Payment cancelled. Your seat was released.');
      } else {
        toastError(err.response?.data?.detail || err.message || 'Failed to book slot.');
      }
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

  const groupedSlots = useMemo(() => {
    const groups = {};
    [...slots]
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
      .forEach((slot) => {
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
  }, [slots]);

  return (
    <div className="space-y-6">
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
          {hasActiveFilters && (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleClearFilters}
              icon={X}
            >
              Reset filters
            </Button>
          )}
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

      <div className="bg-white border border-zinc-200 rounded-xl p-4 shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-zinc-600 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-zinc-400" />
              Business
            </label>
            <select
              value={businessId}
              onChange={(e) => setBusinessId(e.target.value)}
              className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-1.5 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all cursor-pointer"
            >
              <option value="">All Businesses</option>
              {businesses.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.business_name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-medium text-zinc-600 flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5 text-zinc-400" />
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-1.5 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all cursor-pointer"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-medium text-zinc-600 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-zinc-400" />
              From Date
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-1.5 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all"
            />
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-medium text-zinc-600 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-zinc-400" />
              To Date
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-1.5 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-zinc-100">
          <div className="flex items-center gap-1.5 p-1 bg-zinc-100 rounded-lg border border-zinc-200/60">
            <button
              type="button"
              onClick={() => setStatusFilter('AVAILABLE')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
                statusFilter === 'AVAILABLE'
                  ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              Available
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter('WAITLIST')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
                statusFilter === 'WAITLIST'
                  ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              Waitlist
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter('ALL')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
                statusFilter === 'ALL'
                  ? 'bg-white text-zinc-900 font-semibold shadow-xs'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              All Slots
            </button>
          </div>

          <span className="text-xs text-zinc-400">
            {slots.length} {slots.length === 1 ? 'slot found' : 'slots found'}
          </span>
        </div>
      </div>

      {loading ? (
        <SkeletonCard count={6} />
      ) : Object.keys(groupedSlots).length === 0 ? (
        <EmptyState
          icon={CalendarDays}
          title="No slots found"
          description={
            hasActiveFilters
              ? 'No appointment slots match the selected criteria.'
              : 'There are currently no slots published in the system.'
          }
          action={
            hasActiveFilters ? (
              <Button variant="secondary" size="sm" onClick={handleClearFilters}>
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
        <div className="space-y-8">
          {Object.entries(groupedSlots).map(([dayLabel, daySlots]) => (
            <section key={dayLabel} className="space-y-3">
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
                        <div className="flex items-start justify-between gap-2 pb-3 mb-3 border-b border-zinc-100">
                          <div>
                            {slot.business_name && (
                              <div className="text-xs font-semibold text-blue-600 mb-0.5 tracking-tight">
                                {slot.business_name}
                              </div>
                            )}
                            <h3 className="text-sm font-semibold text-zinc-900 tracking-tight">
                              {slot.resource_id}
                            </h3>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              {slot.category && (
                                <span className="text-[11px] font-medium text-zinc-500 uppercase tracking-wider">
                                  {slot.category.replace('_', ' ')}
                                </span>
                              )}
                              <span className="text-[11px] font-mono text-zinc-400">
                                {slot.id}
                              </span>
                            </div>
                          </div>
                          <Badge status={slot.status} size="sm" />
                        </div>

                        <div className="space-y-2 text-xs">
                          <div className="flex items-center gap-2 text-zinc-700 font-medium">
                            <Clock className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                            <span>
                              {formatLocalTimeRange(slot.start_time, slot.end_time)}
                            </span>
                          </div>

                          {slot.capacity > 1 && (
                            <div className="flex items-center justify-between">
                              <span className="text-[11px] text-zinc-500">Accommodates</span>
                              <span className="font-medium text-zinc-800">{slot.capacity} people</span>
                            </div>
                          )}

                          <div className="flex items-center justify-between pt-1">
                            <span className="text-[11px] text-zinc-500">Session fee</span>
                            <span className="font-semibold text-zinc-900">
                              {formatCurrency(slot.price)}
                            </span>
                          </div>
                        </div>
                      </div>

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
                            {Number(slot.price) > 0 ? 'Book & pay' : 'Book slot'}
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
