import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  if (value === undefined || value === null) return '-';
  return `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatPercent(value: number): string {
  if (value === undefined || value === null) return '-';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export function getChangeColor(value: number): string {
  if (value > 0) return 'text-buy';
  if (value < 0) return 'text-sell';
  return 'text-hold';
}

export function getSignalBgColor(signal: string): string {
  switch (signal) {
    case 'BUY': return 'bg-buy';
    case 'SELL': return 'bg-sell';
    default: return 'bg-hold';
  }
}

export function getSignalTextColor(signal: string): string {
  switch (signal) {
    case 'BUY': return 'text-buy';
    case 'SELL': return 'text-sell';
    default: return 'text-hold';
  }
}

export function timeAgo(dateString: string): string {
  if (!dateString) return '-';
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
