// API client for AI Trader backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

export const api = {
  health: () => fetchApi<any>('/api/health'),
  
  prices: {
    all: (index?: string) => fetchApi<any>(`/api/prices/${index ? `?index=${index}` : ''}`),
    one: (symbol: string) => fetchApi<any>(`/api/prices/${symbol}`),
    indices: () => fetchApi<any>('/api/prices/indices/summary'),
    nifty50: () => fetchApi<any>('/api/prices/indices/nifty50'),
    niftybank: () => fetchApi<any>('/api/prices/indices/niftybank'),
  },
  
  signals: {
    all: (index?: string, signalType?: string) => {
      const params = new URLSearchParams();
      if (index) params.append('index', index);
      if (signalType) params.append('signal_type', signalType);
      const query = params.toString() ? `?${params.toString()}` : '';
      return fetchApi<any>(`/api/signals/${query}`);
    },
    one: (symbol: string) => fetchApi<any>(`/api/signals/${symbol}`),
    overview: () => fetchApi<any>('/api/signals/summary/overview'),
    bullish: (limit?: number) => fetchApi<any>(`/api/signals/trending/bullish${limit ? `?limit=${limit}` : ''}`),
    bearish: (limit?: number) => fetchApi<any>(`/api/signals/trending/bearish${limit ? `?limit=${limit}` : ''}`),
  },
};
