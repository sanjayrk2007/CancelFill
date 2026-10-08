import { useState } from 'react';
import { NavLink, useNavigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { useToast } from '../context/useToast';
import Badge from './ui/Badge';
import {
  CalendarDays,
  Sparkles,
  Clock,
  CheckCircle,
  BarChart3,
  Users,
  LogOut,
  LogIn,
  UserPlus,
  Menu,
  X,
  Layers,
} from 'lucide-react';

import { useOffers } from '../context/useOffers';

export default function Layout() {
  const { user, role, logout } = useAuth();
  const { success } = useToast();
  const { activeOffersCount } = useOffers();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    success('You have been logged out.');
    navigate('/login');
  };

  const customerLinks = [
    { to: '/slots', label: 'Browse Slots', icon: CalendarDays },
    { to: '/offers', label: 'My Offers', icon: Sparkles, badge: activeOffersCount },
    { to: '/bookings', label: 'My Bookings', icon: CheckCircle },
    { to: '/waitlist', label: 'My Waitlist', icon: Clock },
  ];

  const businessLinks = [
    { to: '/business/dashboard', label: 'Dashboard', icon: BarChart3 },
    { to: '/business/slots', label: 'Manage Slots', icon: Layers },
    { to: '/business/waitlist', label: 'Waitlists', icon: Users },
    { to: '/business/bookings', label: 'Bookings', icon: CheckCircle },
  ];

  const activeLinks = role === 'BUSINESS' ? businessLinks : role === 'CUSTOMER' ? customerLinks : [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Background ambient subtle glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-gradient-to-b from-indigo-600/10 via-purple-600/5 to-transparent blur-3xl opacity-70" />
      </div>

      {/* Top Navigation */}
      <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Brand */}
          <div className="flex items-center gap-8">
            <NavLink
              to={role === 'BUSINESS' ? '/business/dashboard' : role === 'CUSTOMER' ? '/slots' : '/login'}
              className="flex items-center gap-2.5 font-bold text-xl tracking-tight text-white hover:opacity-90 transition-opacity"
            >
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-md shadow-indigo-500/30 border border-indigo-400/30">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <span className="bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
                CancelFill
              </span>
            </NavLink>

            {/* Desktop Nav Links */}
            {user && (
              <nav className="hidden md:flex items-center gap-1">
                {activeLinks.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        `flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-medium transition-all duration-150 ${
                          isActive
                            ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 shadow-sm'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80'
                        }`
                      }
                    >
                      <Icon className="w-4 h-4" />
                      <span>{item.label}</span>
                      {typeof item.badge === 'number' && item.badge > 0 && (
                        <span className="ml-1 px-1.5 py-0.2 text-[11px] font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-xs animate-pulse">
                          {item.badge}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
              </nav>
            )}
          </div>

          {/* Right Header: User info or Auth buttons */}
          <div className="hidden md:flex items-center gap-4">
            {user ? (
              <div className="flex items-center gap-3">
                <div className="flex flex-col items-end">
                  <span className="text-sm font-semibold text-white leading-tight">{user.name}</span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-xs text-slate-400">{user.email}</span>
                    <Badge size="sm" status={user.role}>
                      {user.role}
                    </Badge>
                  </div>
                </div>

                <div className="h-6 w-px bg-slate-800" />

                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all cursor-pointer"
                  title="Log out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Logout</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <NavLink
                  to="/login"
                  className={({ isActive }) =>
                    `flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-slate-800 text-white'
                        : 'text-slate-300 hover:text-white hover:bg-slate-900'
                    }`
                  }
                >
                  <LogIn className="w-4 h-4" />
                  <span>Sign In</span>
                </NavLink>
                <NavLink
                  to="/register"
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition-all"
                >
                  <UserPlus className="w-4 h-4" />
                  <span>Register</span>
                </NavLink>
              </div>
            )}
          </div>

          {/* Mobile hamburger button */}
          <div className="flex md:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-slate-800 bg-slate-950/95 backdrop-blur-xl px-4 py-3 space-y-2">
            {user && (
              <div className="pb-3 mb-2 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-white">{user.name}</div>
                  <div className="text-xs text-slate-400">{user.email}</div>
                </div>
                <Badge size="sm" status={user.role}>
                  {user.role}
                </Badge>
              </div>
            )}

            {user &&
              activeLinks.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileMenuOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium ${
                        isActive
                          ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                      }`
                    }
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className="w-4 h-4" />
                      <span>{item.label}</span>
                    </div>
                    {typeof item.badge === 'number' && item.badge > 0 && (
                      <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                );
              })}

            {user ? (
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
                className="w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-sm font-medium text-rose-400 hover:bg-rose-500/10"
              >
                <LogOut className="w-4 h-4" />
                <span>Log Out</span>
              </button>
            ) : (
              <div className="pt-2 flex flex-col gap-2">
                <NavLink
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-4 py-2 text-center rounded-xl text-sm font-medium bg-slate-900 text-slate-200"
                >
                  Sign In
                </NavLink>
                <NavLink
                  to="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-4 py-2 text-center rounded-xl text-sm font-medium bg-indigo-600 text-white"
                >
                  Register
                </NavLink>
              </div>
            )}
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/60 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>CancelFill — Automated Cancellation Recovery & Waitlist Platform</span>
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Backend API Connected
          </span>
        </div>
      </footer>
    </div>
  );
}
