import { useState } from 'react';
import { NavLink, useNavigate, Outlet } from 'react-router-dom';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Dialog from '@radix-ui/react-dialog';
import { useAuth } from '../context/useAuth';
import { useToast } from '../context/useToast';
import { useOffers } from '../context/useOffers';
import Avatar from './ui/Avatar';
import Badge from './ui/Badge';
import Button from './ui/Button';
import {
  CalendarDays,
  Sparkles,
  Clock,
  CheckCircle,
  BarChart3,
  Users,
  LogOut,
  User as UserIcon,
  Menu,
  X,
  Layers,
  ChevronDown,
} from 'lucide-react';

export default function Layout() {
  const { user, role, logout } = useAuth();
  const { success } = useToast();
  const { activeOffersCount } = useOffers();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profileDialogOpen, setProfileDialogOpen] = useState(false);

  const handleLogout = () => {
    logout();
    success('You have been logged out.');
    navigate('/login');
  };

  const customerLinks = [
    { to: '/slots', label: 'Slots', icon: CalendarDays },
    { to: '/offers', label: 'Offers', icon: Sparkles, badge: activeOffersCount },
    { to: '/bookings', label: 'Bookings', icon: CheckCircle },
    { to: '/waitlist', label: 'Waitlist', icon: Clock },
  ];

  const businessLinks = [
    { to: '/business/dashboard', label: 'Dashboard', icon: BarChart3 },
    { to: '/business/slots', label: 'Slots', icon: Layers },
    { to: '/business/waitlist', label: 'Waitlist', icon: Users },
    { to: '/business/bookings', label: 'Bookings', icon: CheckCircle },
  ];

  const activeLinks = role === 'BUSINESS' ? businessLinks : role === 'CUSTOMER' ? customerLinks : [];

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 flex flex-col font-sans">
      {/* Top Header */}
      <header className="sticky top-0 z-40 w-full bg-white/95 backdrop-blur-xs border-b border-zinc-200">
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          {/* Brand Wordmark & Nav */}
          <div className="flex items-center gap-6">
            <NavLink
              to={role === 'BUSINESS' ? '/business/dashboard' : role === 'CUSTOMER' ? '/slots' : '/login'}
              className="flex items-center gap-2 font-semibold text-base tracking-tight text-zinc-900 hover:text-blue-600 transition-colors"
            >
              <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center text-white text-xs font-bold shadow-xs">
                C
              </div>
              <span>CancelFill</span>
            </NavLink>

            {/* Desktop Navigation Links */}
            {user && (
              <nav className="hidden md:flex items-center gap-1">
                {activeLinks.map((item) => {
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                          isActive
                            ? 'bg-zinc-100 text-zinc-900 font-semibold'
                            : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
                        }`
                      }
                    >
                      <span>{item.label}</span>
                      {typeof item.badge === 'number' && item.badge > 0 && (
                        <span className="ml-1 px-1.5 py-0.2 text-[10px] font-bold rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                          {item.badge}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
              </nav>
            )}
          </div>

          {/* Right Header Area */}
          <div className="hidden md:flex items-center gap-3">
            {user ? (
              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <button
                    type="button"
                    className="flex items-center gap-2.5 p-1 rounded-lg hover:bg-zinc-100 transition-colors text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 cursor-pointer"
                    aria-label="User account menu"
                  >
                    <Avatar name={user.name} size="sm" />
                    <div className="flex flex-col text-xs leading-none">
                      <span className="font-medium text-zinc-900">{user.name}</span>
                      <span className="text-[11px] text-zinc-500 mt-0.5">{role}</span>
                    </div>
                    <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />
                  </button>
                </DropdownMenu.Trigger>

                <DropdownMenu.Portal>
                  <DropdownMenu.Content
                    align="end"
                    sideOffset={6}
                    className="z-50 min-w-[200px] rounded-xl bg-white p-1.5 shadow-lg border border-zinc-200 text-zinc-900 duration-150 animate-in fade-in-0 zoom-in-95 focus:outline-none"
                  >
                    <div className="px-2.5 py-2">
                      <div className="text-xs font-semibold text-zinc-900">{user.name}</div>
                      <div className="text-[11px] text-zinc-500 truncate">{user.email}</div>
                      <div className="mt-1.5">
                        <Badge status={role} size="sm" />
                      </div>
                    </div>

                    <DropdownMenu.Separator className="h-px bg-zinc-100 my-1" />

                    <DropdownMenu.Item
                      onSelect={() => setProfileDialogOpen(true)}
                      className="flex items-center gap-2 px-2.5 py-1.5 text-xs text-zinc-700 rounded-md hover:bg-zinc-100 hover:text-zinc-900 cursor-pointer focus:outline-none focus:bg-zinc-100"
                    >
                      <UserIcon className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Profile</span>
                    </DropdownMenu.Item>

                    <DropdownMenu.Separator className="h-px bg-zinc-100 my-1" />

                    <DropdownMenu.Item
                      onSelect={handleLogout}
                      className="flex items-center gap-2 px-2.5 py-1.5 text-xs text-rose-600 rounded-md hover:bg-rose-50 hover:text-rose-700 cursor-pointer focus:outline-none focus:bg-rose-50"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Sign out</span>
                    </DropdownMenu.Item>
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>
            ) : (
              <div className="flex items-center gap-2">
                <NavLink
                  to="/login"
                  className="px-3 py-1.5 text-xs font-medium text-zinc-700 hover:text-zinc-900 rounded-md transition-colors"
                >
                  Sign In
                </NavLink>
                <NavLink
                  to="/register"
                  className="px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-xs transition-colors"
                >
                  Register
                </NavLink>
              </div>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 rounded-md text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown drawer (375px) */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-zinc-200 bg-white px-4 py-3 space-y-2">
            {user && (
              <div className="pb-3 border-b border-zinc-100 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Avatar name={user.name} size="sm" />
                  <div>
                    <div className="text-xs font-semibold text-zinc-900">{user.name}</div>
                    <div className="text-[11px] text-zinc-500">{user.email}</div>
                  </div>
                </div>
                <Badge status={role} size="sm" />
              </div>
            )}

            {user &&
              activeLinks.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium ${
                      isActive
                        ? 'bg-zinc-100 text-zinc-900 font-semibold'
                        : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
                    }`
                  }
                >
                  <span>{item.label}</span>
                  {typeof item.badge === 'number' && item.badge > 0 && (
                    <span className="px-1.5 py-0.2 text-[10px] font-bold rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              ))}

            {user ? (
              <div className="pt-2 border-t border-zinc-100 flex flex-col gap-1">
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    setProfileDialogOpen(true);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-xs font-medium text-zinc-700 hover:bg-zinc-50 text-left"
                >
                  <UserIcon className="w-4 h-4 text-zinc-500" />
                  <span>Profile</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    handleLogout();
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-xs font-medium text-rose-600 hover:bg-rose-50 text-left"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign out</span>
                </button>
              </div>
            ) : (
              <div className="pt-2 border-t border-zinc-100 flex flex-col gap-2">
                <NavLink
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 text-center rounded-md text-xs font-medium text-zinc-700 hover:bg-zinc-100"
                >
                  Sign In
                </NavLink>
                <NavLink
                  to="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 text-center rounded-md text-xs font-medium bg-blue-600 text-white"
                >
                  Register
                </NavLink>
              </div>
            )}
          </div>
        )}
      </header>

      {/* Main Content Area: max content width 1100px */}
      <main className="flex-1 max-w-[1100px] w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-200 bg-white py-5 text-xs text-zinc-500">
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>CancelFill — Automated Cancellation Recovery & Waitlist System</span>
          <span className="text-zinc-400">All local times in your timezone</span>
        </div>
      </footer>

      {/* Profile Dialog */}
      <Dialog.Root open={profileDialogOpen} onOpenChange={setProfileDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30 backdrop-blur-xs animate-in fade-in-0 duration-150" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl border border-zinc-200 duration-150 animate-in fade-in-0 zoom-in-95 focus:outline-none">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
              <Dialog.Title className="text-sm font-semibold text-zinc-900">
                User Profile
              </Dialog.Title>
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="text-zinc-400 hover:text-zinc-600 p-1 rounded-md"
                  aria-label="Close"
                >
                  <X className="w-4 h-4" />
                </button>
              </Dialog.Close>
            </div>

            {user && (
              <div className="mt-4 space-y-4 text-xs">
                <div className="flex items-center gap-3">
                  <Avatar name={user.name} size="lg" />
                  <div>
                    <div className="text-sm font-semibold text-zinc-900">{user.name}</div>
                    <div className="text-zinc-500">{user.email}</div>
                  </div>
                </div>

                <div className="bg-zinc-50 border border-zinc-100 rounded-lg p-3 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-500">Role</span>
                    <Badge status={role} size="sm" />
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-500">Account ID</span>
                    <span className="font-mono text-zinc-700">{user.id}</span>
                  </div>
                </div>
              </div>
            )}

            <div className="mt-5 pt-3 border-t border-zinc-100 flex justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setProfileDialogOpen(false)}
              >
                Close
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
