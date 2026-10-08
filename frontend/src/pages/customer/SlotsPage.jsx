import { useState, useEffect, useCallback } from 'react';
import client from '../../api/client';
import { useToast } from '../../context/useToast';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Spinner from '../../components/ui/Spinner';
import EmptyState from '../../components/ui/EmptyState';
import { formatLocalDateTime, formatLocalTimeRange, formatCurrency } from '../../lib/formatters';
import {
  CalendarDays,
  Clock,
  DollarSign,
  RotateCw,
  AlertCircle,
  CalendarCheck,
  UserPlus,
  Layers,
} from 'lucide-react';

export default function SlotsPage() {
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const { success, error: toastError } = useToast();

  const fetchSlots = useCallback(async (isRefresh = false) => {
    if (!isRefresh) setLoading(true);
    setError(null);
    try {
      const response = await client.get('/api/v1/slots');
      setSlots(response.data || []);
    } catch (err) {
      console.error('Error fetching slots:', err);
      setError(err.response?.data?.detail || 'Failed to load slots. Please check backend connection.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSlots();
  }, [fetchSlots]);

  const handleBookNow = async (slot) => {
    setActionLoadingId(slot.id);
    try {
      await client.post('/api/v1/bookings', { slot_id: slot.id });
      success(`Successfully booked ${slot.resource_id}!`);
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
      success(`Added to waitlist for ${slot.resource_id}!`);
      await fetchSlots(true);
    } catch (err) {
      const message = err.response?.data?.detail || 'Failed to join waitlist.';
      toastError(message);
      await fetchSlots(true);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Filter slots
  const filteredSlots = slots.filter((slot) => {
    if (statusFilter === 'ALL') return true;
    return slot.status === statusFilter;
  });

  // Calculate status counts
  const counts = {
    ALL: slots.length,
    AVAILABLE: slots.filter((s) => s.status === 'AVAILABLE').length,
    BOOKED: slots.filter((s) => s.status === 'BOOKED').length,
    HELD: slots.filter((s) => s.status === 'HELD').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/60">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Appointment Slots
            </h1>
            <Badge status="AVAILABLE">LIVE</Badge>
          </div>
          <p className="text-sm text-slate-400">
            Browse schedule openings, reserve appointments, or join the priority waitlist.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchSlots(true)}
            icon={RotateCw}
            disabled={loading}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        {['ALL', 'AVAILABLE', 'BOOKED', 'HELD'].map((filterKey) => {
          const isActive = statusFilter === filterKey;
          return (
            <button
              key={filterKey}
              onClick={() => setStatusFilter(filterKey)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150 flex items-center gap-1.5 cursor-pointer ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'bg-slate-900/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800'
              }`}
            >
              <span>{filterKey === 'ALL' ? 'All Slots' : filterKey.charAt(0) + filterKey.slice(1).toLowerCase()}</span>
              <span
                className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                  isActive ? 'bg-indigo-700 text-indigo-100' : 'bg-slate-800 text-slate-400'
                }`}
              >
                {counts[filterKey] || 0}
              </span>
            </button>
          );
        })}
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <span className="text-sm font-medium">{error}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={() => fetchSlots(false)}>
            Retry
          </Button>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="min-h-[350px] flex flex-col items-center justify-center gap-3 p-12 border border-slate-800/80 rounded-2xl bg-slate-900/30">
          <Spinner size="lg" />
          <p className="text-sm text-slate-400">Loading appointment slots...</p>
        </div>
      ) : filteredSlots.length === 0 ? (
        /* Empty States */
        slots.length === 0 ? (
          <Card>
            <CardContent className="pt-6">
              <EmptyState
                icon={CalendarDays}
                title="No Slots Available"
                description="There are currently no slots published in the system. Check back later or ask your provider."
                action={
                  <Button variant="secondary" size="sm" onClick={() => fetchSlots(false)}>
                    Check Again
                  </Button>
                }
              />
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="pt-6">
              <EmptyState
                icon={Layers}
                title={`No ${statusFilter.toLowerCase()} slots found`}
                description={`There are currently no slots with status "${statusFilter}".`}
                action={
                  <Button variant="secondary" size="sm" onClick={() => setStatusFilter('ALL')}>
                    Show All Slots
                  </Button>
                }
              />
            </CardContent>
          </Card>
        )
      ) : (
        /* Slot Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredSlots.map((slot) => {
            const isAvailable = slot.status === 'AVAILABLE';
            const isBookedOrHeld = slot.status === 'BOOKED' || slot.status === 'HELD';
            const isProcessing = actionLoadingId === slot.id;

            return (
              <Card
                key={slot.id}
                hover
                className="flex flex-col justify-between border-slate-800 bg-slate-900/90 hover:border-slate-700 transition-all"
              >
                <div>
                  <CardHeader className="pb-3 border-b border-slate-800/60">
                    <div className="flex items-start justify-between gap-2">
                      <div className="truncate">
                        <CardTitle className="text-base truncate" title={slot.resource_id}>
                          {slot.resource_id}
                        </CardTitle>
                        <CardDescription className="text-xs text-slate-400 mt-0.5 truncate">
                          ID: {slot.id}
                        </CardDescription>
                      </div>
                      <Badge status={slot.status} size="sm" />
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-3 pt-1">
                    {/* Local Start Time & Range */}
                    <div className="flex items-start gap-2.5 text-slate-300">
                      <Clock className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
                      <div className="text-xs">
                        <div className="font-semibold text-slate-200">
                          {formatLocalDateTime(slot.start_time)}
                        </div>
                        <div className="text-slate-400 text-[11px] mt-0.5">
                          {formatLocalTimeRange(slot.start_time, slot.end_time)}
                        </div>
                      </div>
                    </div>

                    {/* Price */}
                    <div className="flex items-center gap-2.5 text-slate-300">
                      <DollarSign className="w-4 h-4 text-emerald-400 shrink-0" />
                      <div className="text-xs font-semibold text-emerald-300">
                        {formatCurrency(slot.price)}
                      </div>
                    </div>
                  </CardContent>
                </div>

                {/* Footer Action */}
                <CardFooter className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-end">
                  {isAvailable && (
                    <Button
                      variant="primary"
                      size="sm"
                      isLoading={isProcessing}
                      disabled={isProcessing}
                      onClick={() => handleBookNow(slot)}
                      icon={CalendarCheck}
                      className="w-full sm:w-auto"
                    >
                      Book now
                    </Button>
                  )}

                  {isBookedOrHeld && (
                    <Button
                      variant="secondary"
                      size="sm"
                      isLoading={isProcessing}
                      disabled={isProcessing}
                      onClick={() => handleJoinWaitlist(slot)}
                      icon={UserPlus}
                      className="w-full sm:w-auto hover:border-sky-500/50 hover:text-sky-300"
                    >
                      Join waitlist
                    </Button>
                  )}

                  {!isAvailable && !isBookedOrHeld && (
                    <span className="text-xs text-slate-500 italic">No actions available</span>
                  )}
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
