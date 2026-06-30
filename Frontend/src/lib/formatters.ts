import { formatDistanceToNowStrict } from 'date-fns';

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return `${date.toLocaleString()} (${formatDistanceToNowStrict(date, { addSuffix: true })})`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }

  return date.toLocaleString();
}

export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }

  return formatDistanceToNowStrict(date, { addSuffix: true });
}

export function formatDurationRange(
  startedAt: string | null | undefined,
  finishedAt: string | null | undefined,
): string {
  if (!startedAt) {
    return '—';
  }

  const start = new Date(startedAt);
  if (Number.isNaN(start.getTime())) {
    return '—';
  }

  const end = finishedAt ? new Date(finishedAt) : new Date();
  if (Number.isNaN(end.getTime())) {
    return '—';
  }

  const totalSeconds = Math.max(0, Math.floor((end.getTime() - start.getTime()) / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }

  return `${seconds}s`;
}

export function formatCurrencyCents(value: number | null | undefined): string {
  const cents = value ?? 0;
  return `$${(cents / 100).toFixed(2)}`;
}


