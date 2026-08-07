import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Trader - Indian Stock Trading Signals',
  description: 'Free trading signals for Nifty 50 & Nifty Bank',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-dark-bg">
        {/* Header */}
        <header className="sticky top-0 z-50 bg-dark-card/95 backdrop-blur border-b border-dark-border">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
                  <span className="text-white font-bold text-lg">AI</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold">AI Trader</h1>
                  <p className="text-xs text-gray-400">Nifty & Bank • Phase 1</p>
                </div>
              </div>
              
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-2 h-2 rounded-full bg-buy live-pulse"></span>
                  <span className="text-gray-400">Live</span>
                </div>
                <time className="text-sm text-gray-400 hidden sm:block">
                  {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                </time>
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-dark-border py-4 mt-8">
          <div className="container mx-auto px-4 text-center text-sm text-gray-500">
            <p>AI Trader • Free Trading Signals • Phase 1: Rule-Based</p>
            <p className="text-xs mt-1">Data: Yahoo Finance | Not financial advice</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
