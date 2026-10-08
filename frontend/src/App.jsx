import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/useAuth';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Spinner from './components/ui/Spinner';

import Login from './pages/Login';
import Register from './pages/Register';
import NotFound from './pages/NotFound';

import SlotsPage from './pages/customer/SlotsPage';
import OffersPage from './pages/customer/OffersPage';
import BookingsPage from './pages/customer/BookingsPage';
import WaitlistPage from './pages/customer/WaitlistPage';

import BusinessSlotsPage from './pages/business/BusinessSlotsPage';
import BusinessWaitlistPage from './pages/business/BusinessWaitlistPage';
import BusinessBookingsPage from './pages/business/BusinessBookingsPage';
import BusinessStatsPage from './pages/business/BusinessStatsPage';

function HomeRedirect() {
  const { user, role, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={role === 'BUSINESS' ? '/business/slots' : '/slots'} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        {/* Index redirect based on auth/role state */}
        <Route index element={<HomeRedirect />} />

        {/* Public auth routes */}
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />

        {/* Customer protected routes (P7b) */}
        <Route
          path="slots"
          element={
            <ProtectedRoute allowedRoles={['CUSTOMER']}>
              <SlotsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="offers"
          element={
            <ProtectedRoute allowedRoles={['CUSTOMER']}>
              <OffersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="bookings"
          element={
            <ProtectedRoute allowedRoles={['CUSTOMER']}>
              <BookingsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="waitlist"
          element={
            <ProtectedRoute allowedRoles={['CUSTOMER']}>
              <WaitlistPage />
            </ProtectedRoute>
          }
        />

        {/* Business protected routes (P7c) */}
        <Route
          path="business/slots"
          element={
            <ProtectedRoute allowedRoles={['BUSINESS']}>
              <BusinessSlotsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="business/waitlist"
          element={
            <ProtectedRoute allowedRoles={['BUSINESS']}>
              <BusinessWaitlistPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="business/bookings"
          element={
            <ProtectedRoute allowedRoles={['BUSINESS']}>
              <BusinessBookingsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="business/stats"
          element={
            <ProtectedRoute allowedRoles={['BUSINESS']}>
              <BusinessStatsPage />
            </ProtectedRoute>
          }
        />

        {/* Catch-all 404 */}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
