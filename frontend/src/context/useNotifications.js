import { useContext } from 'react';
import { NotificationsContext } from './NotificationsContextDef';

export function useNotifications() {
  const context = useContext(NotificationsContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationsProvider');
  }
  return context;
}

export default useNotifications;
