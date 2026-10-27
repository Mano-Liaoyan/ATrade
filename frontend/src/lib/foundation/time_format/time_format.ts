// Shows a UTC time from the backend as text. Pages that compare runs show UTC, because the bar ends are UTC.

// YYYY-MM-DDTHH:MM:SS of an ISO 8601 time.
const ISO_SECOND_LENGTH = 19;

export function formatUtcTime(timeUtc: string): string {
  const isoSecond = new Date(timeUtc).toISOString().slice(0, ISO_SECOND_LENGTH);
  return `${isoSecond.replace('T', ' ')} UTC`;
}
