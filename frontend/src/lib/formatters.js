/**
 * Format an ISO date/time string to the user's local date and time string.
 * Example: "Thu, Oct 8, 2026, 10:00 AM"
 */
export function formatLocalDateTime(isoString) {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    return new Intl.DateTimeFormat(undefined, {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  } catch {
    return isoString;
  }
}

/**
 * Format slot time range in the user's local time.
 * Example: "10:00 AM – 11:00 AM"
 */
export function formatLocalTimeRange(startIso, endIso) {
  if (!startIso) return '—';
  try {
    const start = new Date(startIso);
    const timeFormatter = new Intl.DateTimeFormat(undefined, {
      hour: 'numeric',
      minute: '2-digit',
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
 * Format a number or string as USD currency.
 * Example: 50 -> "$50.00"
 */
export function formatCurrency(amount) {
  if (amount === undefined || amount === null) return '$0.00';
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return `$${amount}`;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(num);
}

/**
 * Format remaining seconds into MM:SS or HH:MM:SS.
 */
export function formatRemainingSeconds(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0));
  const hrs = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;

  if (hrs > 0) {
    return `${hrs}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}
