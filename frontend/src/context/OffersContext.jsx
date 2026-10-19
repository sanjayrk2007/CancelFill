import { useState, useEffect, useCallback, useRef } from 'react';
import { OffersContext } from './OffersContextDef';
import client from '../api/client';
import { useAuth } from './useAuth';
import { useToast } from './useToast';
import { checkoutAndPay } from '../lib/payments';

export function OffersProvider({ children }) {
  const { user, role } = useAuth();
  const { success, error: toastError } = useToast();

  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(() => Boolean(user && role === 'CUSTOMER'));
  const [error, setError] = useState(null);
  const [inFlightIds, setInFlightIds] = useState(new Set());
  const inFlightRef = useRef(inFlightIds);

  useEffect(() => {
    inFlightRef.current = inFlightIds;
  }, [inFlightIds]);

  const fetchOffers = useCallback(async () => {
    if (!user || role !== 'CUSTOMER') {
      return;
    }

    try {
      const response = await client.get('/api/v1/me/offers');
      setOffers(response.data || []);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch offers:', err);
      setError(err.response?.data?.detail || 'Failed to fetch active offers.');
    } finally {
      setLoading(false);
    }
  }, [user, role]);

  // Polling every 5 seconds for CUSTOMER
  useEffect(() => {
    if (!user || role !== 'CUSTOMER') {
      return;
    }

    let isSubscribed = true;

    // Initial fetch (async)
    fetchOffers();

    const intervalId = setInterval(() => {
      if (isSubscribed) {
        fetchOffers();
      }
    }, 5000);

    return () => {
      isSubscribed = false;
      clearInterval(intervalId);
    };
  }, [user, role, fetchOffers]);

  const acceptOffer = useCallback(async (offerId) => {
    if (inFlightRef.current.has(offerId)) {
      return;
    }

    setInFlightIds((prev) => new Set(prev).add(offerId));

    try {
      let booking;
      try {
        booking = (await client.post(`/api/v1/holds/${offerId}/accept`)).data;
      } catch (err) {
        if (err.response?.status !== 402) throw err;
        booking = await checkoutAndPay({ holdId: offerId, user });
      }
      success('Offer accepted! Your booking has been confirmed.');
      await fetchOffers();
      return booking;
    } catch (err) {
      if (err.cancelled) {
        // Payment not completed counts as declining (SRS 3.12): the offer moves to the next person.
        toastError('Payment not completed, so the offer was released to the next person on the waitlist.');
        await fetchOffers();
      } else if (err.response && err.response.status === 409) {
        toastError(err.response.data?.detail || 'This offer is no longer available');
        await fetchOffers();
      } else {
        const msg = err.response?.data?.detail || err.message || 'Failed to accept offer.';
        toastError(msg);
      }
      throw err;
    } finally {
      setInFlightIds((prev) => {
        const next = new Set(prev);
        next.delete(offerId);
        return next;
      });
    }
  }, [fetchOffers, success, toastError, user]);

  const declineOffer = useCallback(async (offerId) => {
    if (inFlightRef.current.has(offerId)) {
      return;
    }

    setInFlightIds((prev) => new Set(prev).add(offerId));

    try {
      const response = await client.post(`/api/v1/holds/${offerId}/decline`);
      success('Offer declined.');
      await fetchOffers();
      return response.data;
    } catch (err) {
      if (err.response && err.response.status === 409) {
        toastError('This offer is no longer available');
        await fetchOffers();
      } else {
        const msg = err.response?.data?.detail || 'Failed to decline offer.';
        toastError(msg);
      }
      throw err;
    } finally {
      setInFlightIds((prev) => {
        const next = new Set(prev);
        next.delete(offerId);
        return next;
      });
    }
  }, [fetchOffers, success, toastError]);

  const value = {
    offers: user && role === 'CUSTOMER' ? offers : [],
    activeOffersCount: user && role === 'CUSTOMER' ? offers.length : 0,
    loading,
    error,
    inFlightIds,
    refreshOffers: () => {
      setLoading(true);
      fetchOffers();
    },
    acceptOffer,
    declineOffer,
  };

  return <OffersContext.Provider value={value}>{children}</OffersContext.Provider>;
}

export { OffersContext };
export default OffersProvider;
