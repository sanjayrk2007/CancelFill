import { useState, useEffect, useCallback, useRef } from 'react';
import { OffersContext } from './OffersContextDef';
import client from '../api/client';
import { useAuth } from './useAuth';
import { useToast } from './useToast';

export function OffersProvider({ children }) {
  const { user, role } = useAuth();
  const { success, error: toastError } = useToast();

  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [inFlightIds, setInFlightIds] = useState(new Set());
  const inFlightRef = useRef(inFlightIds);

  useEffect(() => {
    inFlightRef.current = inFlightIds;
  }, [inFlightIds]);

  const fetchOffers = useCallback(async (isInitial = false) => {
    if (!user || role !== 'CUSTOMER') {
      setOffers([]);
      setLoading(false);
      return;
    }

    if (isInitial) {
      setLoading(true);
    }

    try {
      const response = await client.get('/api/v1/me/offers');
      setOffers(response.data || []);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch offers:', err);
      // Only set UI error if initial fetch failed
      if (isInitial) {
        setError(err.response?.data?.detail || 'Failed to fetch active offers.');
      }
    } finally {
      if (isInitial) {
        setLoading(false);
      }
    }
  }, [user, role]);

  // Polling every 5 seconds for CUSTOMER
  useEffect(() => {
    if (!user || role !== 'CUSTOMER') {
      setOffers([]);
      setLoading(false);
      return;
    }

    let isSubscribed = true;

    // Initial fetch
    fetchOffers(true);

    const intervalId = setInterval(() => {
      if (isSubscribed) {
        fetchOffers(false);
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
      const response = await client.post(`/api/v1/holds/${offerId}/accept`);
      success('Offer accepted! Your booking has been confirmed.');
      await fetchOffers(false);
      return response.data;
    } catch (err) {
      if (err.response && err.response.status === 409) {
        toastError('This offer is no longer available');
        await fetchOffers(false);
      } else {
        const msg = err.response?.data?.detail || 'Failed to accept offer.';
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

  const declineOffer = useCallback(async (offerId) => {
    if (inFlightRef.current.has(offerId)) {
      return;
    }

    setInFlightIds((prev) => new Set(prev).add(offerId));

    try {
      const response = await client.post(`/api/v1/holds/${offerId}/decline`);
      success('Offer declined.');
      await fetchOffers(false);
      return response.data;
    } catch (err) {
      if (err.response && err.response.status === 409) {
        toastError('This offer is no longer available');
        await fetchOffers(false);
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
    offers,
    activeOffersCount: offers.length,
    loading,
    error,
    inFlightIds,
    refreshOffers: () => fetchOffers(false),
    acceptOffer,
    declineOffer,
  };

  return <OffersContext.Provider value={value}>{children}</OffersContext.Provider>;
}

export { OffersContext };
export default OffersProvider;
