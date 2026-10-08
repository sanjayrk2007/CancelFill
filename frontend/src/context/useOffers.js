import { useContext } from 'react';
import { OffersContext } from './OffersContextDef';

export function useOffers() {
  const context = useContext(OffersContext);
  if (!context) {
    throw new Error('useOffers must be used within an OffersProvider');
  }
  return context;
}

export default useOffers;
