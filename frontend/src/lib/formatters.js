/**
 * Formatting helpers for CancelFill
 * Currency default: INR (en-IN)
 * Date format: "Thu 10 Oct, 6:00 PM" in local time
 */

export const CURRENCY = 'INR';
export const CURRENCY_LOCALE = 'en-IN';

/**
 * Format an ISO date/time string to local time formatted like:
 * "Thu 10 Oct, 6:00 PM"
 */
export function formatLocalDateTime(isoString) {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;

    const weekday = new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(date);
    const day = date.getDate();
    const month = new Intl.DateTimeFormat('en-US', { month: 'short' }).format(date);
    const time = new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(date);

    return `${weekday} ${day} ${month}, ${time}`;
  } catch {
    return isoString;
  }
}

/**
 * Format local date only: "Thu 10 Oct"
 */
export function formatLocalDateOnly(isoString) {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;

    const weekday = new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(date);
    const day = date.getDate();
    const month = new Intl.DateTimeFormat('en-US', { month: 'short' }).format(date);

    return `${weekday} ${day} ${month}`;
  } catch {
    return isoString;
  }
}

/**
 * Format slot time range in the user's local time:
 * "6:00 PM – 7:00 PM"
 */
export function formatLocalTimeRange(startIso, endIso) {
  if (!startIso) return '—';
  try {
    const start = new Date(startIso);
    const timeFormatter = new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
    const startTimeStr = timeFormatter.format(start);

    if (!endIso) return startTimeStr;

    const end = new Date(endIso);
    const endTimeStr = timeFormatter.format(end);
    return `${startTimeStr} – ${endTimeStr}`;
  } catch {
    return `${startIso} – ${endIso}`;
  }
}

/**
 * Format a number or string as INR currency.
 * Example: 50 -> "₹50" or "₹50.00"
 */
export function formatCurrency(amount) {
  if (amount === undefined || amount === null) return '₹0';
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return `₹${amount}`;

  return new Intl.NumberFormat(CURRENCY_LOCALE, {
    style: 'currency',
    currency: CURRENCY,
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(num);
}

/**
 * Format remaining seconds into MM:SS.
 */
export function formatRemainingSeconds(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0));
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}
