import { useState, useEffect } from 'react';
import { useOffers } from '../../context/useOffers';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Spinner from '../../components/ui/Spinner';
import EmptyState from '../../components/ui/EmptyState';
import { formatLocalDateTime, formatLocalTimeRange, formatCurrency, formatRemainingSeconds } from '../../lib/formatters';
import {
  Sparkles,
  Clock,
  DollarSign,
  CheckCircle2,
  XCircle,
  RotateCw,
  AlertCircle,
  Timer,
  Zap,
} from 'lucide-react';

export default function OffersPage() {
  const {
    offers,
    loading,
    error,
    inFlightIds,
    refreshOffers,
    acceptOffer,
    declineOffer,
  } = useOffers();

  // Local ticker to update live countdown every second
  const [currentTime, setCurrentTime] = useState(() => Date.now());
  const [activeAction, setActiveAction] = useState({}); // { [offerId]: 'accept' | 'decline' }

  useEffect(() => {
    const timerId = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);

    return () => clearInterval(timerId);
  }, []);

  const handleAccept = async (offer) => {
    if (inFlightIds.has(offer.id)) return;
    setActiveAction((prev) => ({ ...prev, [offer.id]: 'accept' }));
    try {
      await acceptOffer(offer.id);
    } catch {
      // Handled in context toast
    } finally {
      setActiveAction((prev) => {
        const next = { ...prev };
        delete next[offer.id];
        return next;
      });
    }
  };

  const handleDecline = async (offer) => {
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
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/60">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Exclusive Hold Offers
            </h1>
            {offers.length > 0 ? (
              <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
                {offers.length} ACTIVE
              </span>
            ) : (
              <Badge status="HELD">AUTO-POLLING (5s)</Badge>
            )}
          </div>
          <p className="text-sm text-slate-400">
            A cancelled appointment slot opened for you! Accept before the countdown expires to secure your booking.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={refreshOffers}
            icon={RotateCw}
            disabled={loading}
          >
            Refresh Now
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <span className="text-sm font-medium">{error}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={refreshOffers}>
            Retry
          </Button>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="min-h-[350px] flex flex-col items-center justify-center gap-3 p-12 border border-slate-800/80 rounded-2xl bg-slate-900/30">
          <Spinner size="lg" />
          <p className="text-sm text-slate-400">Checking for active hold offers...</p>
        </div>
      ) : offers.length === 0 ? (
        /* Empty State */
        <Card>
          <CardContent className="pt-6">
            <EmptyState
              icon={Sparkles}
              title="No Active Offers"
              description="You do not have any pending hold offers right now. As soon as a slot you've waitlisted for opens up, your exclusive offer will appear here with an active timer."
              action={
                <Button variant="secondary" size="sm" onClick={refreshOffers} icon={RotateCw}>
                  Check Again
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        /* Active Offers List */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {offers.map((offer) => {
            const expiresMs = new Date(offer.expires_at).getTime();
            const remainingSeconds = Math.max(0, Math.floor((expiresMs - currentTime) / 1000));
            const isExpiringSoon = remainingSeconds < 120 && remainingSeconds > 0;
            const isExpired = remainingSeconds === 0;

            const isInFlight = inFlightIds.has(offer.id);
            const currentAction = activeAction[offer.id];

            return (
              <Card
                key={offer.id}
                className="relative overflow-hidden border-indigo-500/30 bg-gradient-to-b from-slate-900 to-slate-950 shadow-2xl shadow-indigo-950/30 flex flex-col justify-between"
              >
                {/* Ambient glowing top accent */}
                <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />

                <div>
                  <CardHeader className="pb-3 border-b border-slate-800/60">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <Zap className="w-4 h-4 text-amber-400 shrink-0" />
                          <CardTitle className="text-lg text-white">
                            {offer.slot?.resource_id || 'Reserved Appointment'}
                          </CardTitle>
                        </div>
                        <CardDescription className="text-xs text-slate-400 mt-1">
                          Hold ID: {offer.id}
                        </CardDescription>
                      </div>
                      <Badge variant="amber">OFFER ACTIVE</Badge>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4 pt-1">
                    {/* Timer Widget */}
                    <div
                      className={`p-4 rounded-xl border flex items-center justify-between gap-4 transition-colors ${
                        isExpired
                          ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                          : isExpiringSoon
                          ? 'bg-amber-500/10 border-amber-500/30 text-amber-200 animate-pulse'
                          : 'bg-indigo-950/40 border-indigo-500/20 text-indigo-200'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                            isExpired
                              ? 'bg-rose-500/20 text-rose-400'
                              : isExpiringSoon
                              ? 'bg-amber-500/20 text-amber-400'
                              : 'bg-indigo-500/20 text-indigo-400'
                          }`}
                        >
                          <Timer className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="text-xs font-semibold uppercase tracking-wider block text-slate-400">
                            {isExpired ? 'Offer Expired' : 'Time Remaining'}
                          </span>
                          <span className="text-2xl font-mono font-bold tracking-tight">
                            {isExpired ? '00:00' : formatRemainingSeconds(remainingSeconds)}
                          </span>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className="text-xs text-slate-400 block">Status</span>
                        <span className="text-xs font-semibold capitalize">
                          {isExpired ? 'Needs Expiry Check' : 'Temporary Hold'}
                        </span>
                      </div>
                    </div>

                    {/* Slot Info */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-slate-950/50 p-3.5 rounded-xl border border-slate-800/60">
                      <div className="flex items-start gap-2.5">
                        <Clock className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
                        <div>
                          <div className="font-semibold text-slate-200">
                            {formatLocalDateTime(offer.slot?.start_time)}
                          </div>
                          <div className="text-slate-400 text-[11px] mt-0.5">
                            {formatLocalTimeRange(offer.slot?.start_time, offer.slot?.end_time)}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2.5">
                        <DollarSign className="w-4 h-4 text-emerald-400 shrink-0" />
                        <div>
                          <div className="font-semibold text-emerald-300">
                            {formatCurrency(offer.slot?.price)}
                          </div>
                          <div className="text-slate-400 text-[11px]">Appointment Price</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </div>

                {/* Actions with double click protection */}
                <CardFooter className="mt-6 pt-4 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-end gap-3">
                  <Button
                    variant="danger"
                    size="md"
                    className="w-full sm:w-auto"
                    icon={XCircle}
                    disabled={isInFlight}
                    isLoading={isInFlight && currentAction === 'decline'}
                    onClick={() => handleDecline(offer)}
                  >
                    Decline
                  </Button>

                  <Button
                    variant="emerald"
                    size="md"
                    className="w-full sm:w-auto"
                    icon={CheckCircle2}
                    disabled={isInFlight}
                    isLoading={isInFlight && currentAction === 'accept'}
                    onClick={() => handleAccept(offer)}
                  >
                    Accept Offer
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
