import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercent(value: number, showSign = true): string {
  const sign = showSign && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatNumber(value: number): string {
  if (value >= 10000000) return `${(value / 10000000).toFixed(2)} Cr`;
  if (value >= 100000) return `${(value / 100000).toFixed(2)} L`;
  if (value >= 1000) return `${(value / 1000).toFixed(2)} K`;
  return value.toString();
}

export function getChangeColor(value: number): string {
  if (value > 0) return 'text-buy';
  if (value < 0) return 'text-sell';
  return 'text-gray-400';
}

export function getSignalBgColor(signal: string): string {
  switch (signal) {
    case 'BUY': return 'bg-buy';
    case 'SELL': return 'bg-sell';
    case 'HOLD': return 'bg-hold';
    default: return 'bg-gray-500';
  }
}

export function getSignalTextColor(signal: string): string {
  switch (signal) {
    case 'BUY': return 'text-buy';
    case 'SELL': return 'text-sell';
    case 'HOLD': return 'text-hold';
    default: return 'text-gray-400';
  }
}

export function timeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
