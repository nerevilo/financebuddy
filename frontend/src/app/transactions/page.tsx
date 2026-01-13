'use client';

import { InstitutionSidebar } from '@/components/dashboard/InstitutionSidebar';
import { TransactionsTable } from '@/components/transactions/TransactionsTable';
import { refreshAllData } from '@/lib/hooks';
import { ProtectedRoute } from '@/lib/auth';
import Link from 'next/link';

function TransactionsContent() {
  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <InstitutionSidebar onDataChange={refreshAllData} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              {/* Left: Breadcrumb + Title */}
              <div>
                <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                  <Link href="/" className="hover:text-gray-700">Dashboard</Link>
                  <span>/</span>
                  <span className="text-gray-900">Transactions</span>
                </div>
                <h1 className="text-2xl font-bold text-gray-900">All Transactions</h1>
              </div>

              {/* Right: Back to Dashboard */}
              <Link
                href="/"
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
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
        <main className="flex-1 overflow-auto p-6">
          <TransactionsTable />
        </main>
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
