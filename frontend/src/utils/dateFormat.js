// Centralized timezone constant — all dates displayed in IST
export const APP_TIMEZONE = 'Asia/Kolkata';

// Backend sends naive UTC timestamps without Z suffix.
// This ensures JavaScript parses them as UTC before timezone conversion.
const ensureUTC = (dateString) => {
  if (!dateString) return '';
  const s = String(dateString);
  if (s.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(s)) return s;
  return s + 'Z';
};

// Common format: "Feb 23, 2:30 PM"
export const formatDateTime = (dateString) => {
  if (!dateString) return '';
  return new Date(ensureUTC(dateString)).toLocaleString('en-US', {
    timeZone: APP_TIMEZONE,
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};

// Short date: "Feb 23"
export const formatDateShort = (dateString) => {
  if (!dateString) return '';
  return new Date(ensureUTC(dateString)).toLocaleDateString('en-US', {
    timeZone: APP_TIMEZONE,
    month: 'short',
    day: 'numeric',
  });
};

// Full date with year: "Feb 23, 2026"
export const formatDateFull = (dateString) => {
  if (!dateString) return '';
  return new Date(ensureUTC(dateString)).toLocaleDateString('en-US', {
    timeZone: APP_TIMEZONE,
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

// Date with weekday: "Sun, Feb 23, 9:30 AM"
export const formatDateWithWeekday = (dateString) => {
  if (!dateString) return '';
  return new Date(ensureUTC(dateString)).toLocaleString('en-US', {
    timeZone: APP_TIMEZONE,
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};

// Re-export for use in inline calls
export { ensureUTC };
