import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOffers } from '../../context/useOffers';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import Card from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Countdown from '../../components/ui/Countdown';
import EmptyState from '../../components/ui/EmptyState';
import { SkeletonCard } from '../../components/ui/Skeleton';
import { formatLocalDateTime, formatLocalTimeRange, formatCurrency } from '../../lib/formatters';
import {
  Sparkles,
  Clock,
  RotateCw,
  AlertCircle,
  CheckCircle2,
  X,
  Check,
} from 'lucide-react';

export default function OffersPage() {
  useDocumentTitle('Hold Offers');

  const {
    offers,
    loading,
    error,
    inFlightIds,
    refreshOffers,
    acceptOffer,
    declineOffer,
  } = useOffers();

  const navigate = useNavigate();
  const [activeAction, setActiveAction] = useState({}); // { [offerId]: 'accept' | 'decline' }
  const [acceptedOfferId, setAcceptedOfferId] = useState(null);

  const handleAccept = useCallback(async (offer) => {
    if (inFlightIds.has(offer.id)) return;
    setActiveAction((prev) => ({ ...prev, [offer.id]: 'accept' }));
    try {
      await acceptOffer(offer.id);
      setAcceptedOfferId(offer.id);
      // Show short success state, then go to /bookings
      setTimeout(() => {
        navigate('/bookings');
      }, 1200);
    } catch {
      // Handled in context toast
    } finally {
      setActiveAction((prev) => {
        const next = { ...prev };
        delete next[offer.id];
        return next;
      });
    }
  }, [inFlightIds, acceptOffer, navigate]);

  const handleDecline = useCallback(async (offer) => {
    if (inFlightIds.has(offer.id)) return;
    setActiveAction((prev) => ({ ...prev, [offer.id]: 'decline' }));
    try {
      await declineOffer(offer.id);
    } catch {
      // Handled in context toast
    } finally {
      setActiveAction((prev) => {
        const next = { ...prev };
        delete next[offer.id];
        return next;
      });
    }
  }, [inFlightIds, declineOffer]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900">
              Hold Offers
            </h1>
            {offers.length > 0 && (
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                {offers.length} active
              </span>
            )}
          </div>
          <p className="text-xs text-zinc-500">
            Exclusive appointment holds reserved for you from the priority waitlist.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={refreshOffers}
            icon={RotateCw}
            disabled={loading}
            aria-label="Refresh offers"
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
          <Button variant="secondary" size="sm" onClick={refreshOffers}>
            Retry
          </Button>
        </div>
      )}

      {/* Main Content: Stacked offer cards */}
      {loading ? (
        <SkeletonCard count={2} />
      ) : offers.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          title="No active hold offers"
          description="When a cancellation occurs for an appointment slot you have waitlisted, an exclusive hold offer will appear here with an active timer."
          action={
            <Button variant="secondary" size="sm" onClick={refreshOffers} icon={RotateCw}>
              Check again
            </Button>
          }
        />
      ) : (
        <div className="max-w-2xl mx-auto space-y-5">
          {offers.map((offer) => {
            const isAccepted = acceptedOfferId === offer.id;
            const isInFlight = inFlightIds.has(offer.id);
            const currentAction = activeAction[offer.id];

            if (isAccepted) {
              return (
                <div
                  key={offer.id}
                  className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 text-center space-y-2 animate-in fade-in"
                >
                  <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <h3 className="text-sm font-semibold text-emerald-900">
                    Offer accepted!
                  </h3>
                  <p className="text-xs text-emerald-700">
                    Your appointment is confirmed. Redirecting to your bookings...
                  </p>
                </div>
              );
            }

            return (
              <Card
                key={offer.id}
                className="flex flex-col justify-between border-zinc-200 hover:border-zinc-300 transition-all p-6"
              >
                <div>
                  {/* Top Bar: Resource & Badge */}
                  <div className="flex items-start justify-between gap-3 pb-4 mb-4 border-b border-zinc-100">
                    <div>
                      <h3 className="text-base font-semibold text-zinc-900 tracking-tight">
                        {offer.slot?.resource_id || 'Reserved Appointment'}
                      </h3>
                      <span className="text-xs font-mono text-zinc-400">
                        Hold #{offer.id}
                      </span>
                    </div>
                    <Badge status="HELD" size="sm">
                      Hold Active
                    </Badge>
                  </div>

                  {/* Large Countdown Section */}
                  <div className="bg-zinc-50 border border-zinc-100 rounded-xl p-4 mb-5">
                    <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500 block mb-2">
                      Hold Expiration Window
                    </span>
                    <Countdown
                      expiresAt={offer.expires_at}
                      totalDurationSeconds={300}
                      size="lg"
                    />
                  </div>

                  {/* Slot Details */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs py-2">
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5 text-zinc-500">
                        <Clock className="w-3.5 h-3.5" />
                        <span>Date & Time</span>
                      </div>
                      <div className="font-medium text-zinc-900">
                        {formatLocalDateTime(offer.slot?.start_time)}
                      </div>
                      <div className="text-zinc-500 text-[11px]">
                        {formatLocalTimeRange(offer.slot?.start_time, offer.slot?.end_time)}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <span className="text-zinc-500">Appointment Fee</span>
                      <div className="font-semibold text-zinc-900 text-sm">
                        {formatCurrency(offer.slot?.price)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Actions: Accept (primary) & Decline (secondary) */}
                <div className="mt-6 pt-4 border-t border-zinc-100 flex items-center justify-end gap-3">
                  <Button
                    variant="secondary"
                    size="md"
                    icon={X}
                    disabled={isInFlight}
                    isLoading={isInFlight && currentAction === 'decline'}
                    onClick={() => handleDecline(offer)}
                  >
                    Decline
                  </Button>

                  <Button
                    variant="primary"
                    size="md"
                    icon={Check}
                    disabled={isInFlight}
                    isLoading={isInFlight && currentAction === 'accept'}
                    onClick={() => handleAccept(offer)}
                  >
                    Accept Offer
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
