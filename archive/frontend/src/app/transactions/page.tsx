'use client';

import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { InstitutionSidebar } from '@/components/dashboard/InstitutionSidebar';
import { TransactionsTable } from '@/components/transactions/TransactionsTable';
import { ChatSidebar, ChatButton } from '@/components/chat';
import { refreshAllData } from '@/lib/hooks';
import { ProtectedRoute } from '@/lib/auth';
import Link from 'next/link';

function TransactionsTableWithParams() {
  const searchParams = useSearchParams();
  const showUnusualOnly = searchParams.get('unusual') === 'true';
  const monthParam = searchParams.get('month');
  const yearParam = searchParams.get('year');

  const initialMonth = monthParam ? parseInt(monthParam, 10) : null;
  const initialYear = yearParam ? parseInt(yearParam, 10) : null;

  return (
    <TransactionsTable
      initialShowUnusualOnly={showUnusualOnly}
      initialMonth={initialMonth}
      initialYear={initialYear}
    />
  );
}

function TransactionsContent() {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-surface-base">
      {/* Sidebar */}
      <InstitutionSidebar
        onDataChange={refreshAllData}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      {/* Main Content */}
      <div className="lg:ml-72 flex flex-col min-h-screen">
        {/* Mobile header bar with hamburger */}
        <div className="lg:hidden sticky top-0 z-30 bg-surface-sidebar px-4 py-3 flex items-center justify-between">
          <button onClick={() => setIsSidebarOpen(true)} className="p-1">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="text-white font-semibold">Transactions</span>
          <div className="w-6" /> {/* Spacer for centering */}
        </div>

        {/* Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 lg:top-0 z-10">
          <div className="px-4 sm:px-6 py-3 sm:py-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0">
              {/* Left: Breadcrumb + Title */}
              <div>
                <div className="hidden sm:flex items-center gap-2 text-sm text-slate-500 mb-1">
                  <Link href="/" className="hover:text-slate-700">Dashboard</Link>
                  <span>/</span>
                  <span className="text-slate-900">Transactions</span>
                </div>
                <h1 className="text-xl sm:text-2xl font-bold tracking-tighter text-slate-900">All Transactions</h1>
              </div>

              {/* Right: Back to Dashboard */}
              <Link
                href="/"
                className="hidden sm:flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Dashboard
              </Link>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto p-4 sm:p-6">
          <Suspense fallback={<TransactionsTableSkeleton />}>
            <TransactionsTableWithParams />
          </Suspense>
        </main>
      </div>

      {/* Chat Sidebar */}
      <ChatSidebar isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />

      {/* Mobile Chat Button */}
      <ChatButton onClick={() => setIsChatOpen(true)} />

      {/* Desktop Chat Toggle Button */}
      <button
        onClick={() => setIsChatOpen(true)}
        className={`
          fixed bottom-6 right-6 z-30
          hidden lg:flex items-center gap-2
          px-4 py-2.5 rounded-full
          bg-slate-900 text-white shadow-lg
          hover:bg-slate-800 hover:scale-105
          transition-all duration-200
          ${isChatOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}
        `}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
        <span className="text-sm font-medium">Ask Ledgi</span>
      </button>
    </div>
  );
}

function TransactionsTableSkeleton() {
  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 overflow-hidden animate-pulse">
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-4">
          <div className="h-4 w-24 bg-slate-200 rounded"></div>
          <div className="h-8 w-32 bg-slate-200 rounded-lg"></div>
          <div className="h-8 w-32 bg-slate-200 rounded-lg"></div>
        </div>
      </div>
      <div className="divide-y divide-slate-200">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="px-6 py-4 flex items-center gap-6">
            <div className="h-4 w-24 bg-slate-200 rounded"></div>
            <div className="h-4 w-48 bg-slate-200 rounded"></div>
            <div className="h-4 w-32 bg-slate-200 rounded"></div>
            <div className="h-4 w-24 bg-slate-200 rounded"></div>
            <div className="h-4 w-16 bg-slate-200 rounded ml-auto"></div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TransactionsPage() {
  return (
    <ProtectedRoute>
      <TransactionsContent />
    </ProtectedRoute>
  );
}
