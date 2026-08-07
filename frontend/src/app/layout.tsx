import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Trader v2.0 - ARTH AI Trading Agent',
  description: 'Self-learning AI trading signals for Nifty 50 & Nifty Bank',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen" style={{ backgroundColor: '#0F172A', color: '#F8FAFC' }}>
        {/* Header */}
        <header className="sticky top-0 z-50 backdrop-blur-lg" style={{ backgroundColor: 'rgba(30, 41, 59, 0.95)', borderBottom: '1px solid #334155' }}>
          <div className="max-w-7xl mx-auto px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #3B82F6, #8B5CF6)' }}>
                  <span className="text-white font-bold text-sm">🤖</span>
                </div>
                <div>
                  <h1 className="text-lg font-bold">AI Trader <span className="text-xs font-normal" style={{ color: '#94A3B8' }}>v2.0</span></h1>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>ARTH AI Agent • Self-Learning</p>
                </div>
              </div>
              
              <nav className="hidden md:flex items-center gap-1">
                <a href="/" className="nav-tab">Dashboard</a>
                <a href="/arth" className="nav-tab">ARTH</a>
                <a href="/backtest" className="nav-tab">Backtest</a>
                <a href="/brain" className="nav-tab">Brain</a>
                <a href="/paper" className="nav-tab">Paper Trade</a>
              </nav>
              
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-2 h-2 rounded-full live-pulse" style={{ backgroundColor: '#10B981' }}></span>
                  <span style={{ color: '#94A3B8' }}>Live</span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Mobile Nav */}
          <div className="md:hidden flex gap-1 px-4 pb-2 overflow-x-auto">
            <a href="/" className="nav-tab text-xs whitespace-nowrap">Dashboard</a>
            <a href="/arth" className="nav-tab text-xs whitespace-nowrap">ARTH</a>
            <a href="/backtest" className="nav-tab text-xs whitespace-nowrap">Backtest</a>
            <a href="/brain" className="nav-tab text-xs whitespace-nowrap">Brain</a>
            <a href="/paper" className="nav-tab text-xs whitespace-nowrap">Paper Trade</a>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer style={{ borderTop: '1px solid #334155', marginTop: '2rem' }}>
          <div className="max-w-7xl mx-auto px-4 py-4 text-center text-sm" style={{ color: '#64748B' }}>
            <p>AI Trader v2.0 • ARTH Self-Learning AI Agent • Indian Markets (NSE)</p>
            <p className="text-xs mt-1">Data: Yahoo Finance (FREE) | Not financial advice | Do your own research</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
