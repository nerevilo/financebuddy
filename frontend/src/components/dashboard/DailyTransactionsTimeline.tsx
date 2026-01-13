'use client';

import { useState, useEffect } from 'react';
import { useTransactionsByPeriod } from '@/lib/hooks';
import { TransactionDetailModal } from '../transactions/TransactionDetailModal';

interface TransactionForModal {
  id: string;
  merchant: string | null;
  category: string | null;
  amount: number;
  description: string;
  date?: string;
  time?: string;
  emoji?: string;
}

interface DailyTransactionsTimelineProps {
  period: 'day' | 'week' | 'month';
}

export function DailyTransactionsTimeline({ period }: DailyTransactionsTimelineProps) {
  const { transactions: data, isLoading } = useTransactionsByPeriod(period);
  const [expandedDay, setExpandedDay] = useState<string | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<TransactionForModal | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Auto-expand first day when data loads
  useEffect(() => {
    if (data.length > 0 && !expandedDay) {
      setExpandedDay(data[0].date);
    }
  }, [data, expandedDay]);

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
    }
  };

  // Show skeleton only on first load (no cached data)
  if (isLoading && data.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
          <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <p className="text-gray-600">No transactions for this period</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily Transactions</h3>

      <div className="space-y-3">
        {data.map((day) => (
          <div key={day.date} className="border border-gray-200 rounded-lg overflow-hidden">
            {/* Day Header */}
            <button
              onClick={() => setExpandedDay(expandedDay === day.date ? null : day.date)}
              className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition"
            >
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${expandedDay === day.date ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500'}`}>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={expandedDay === day.date ? "M19 9l-7 7-7-7" : "M9 5l7 7-7 7"} />
                  </svg>
                </div>
                <div className="text-left">
                  <div className="font-semibold text-gray-900">{formatDate(day.date)}</div>
                  <div className="text-sm text-gray-500">
                    {day.transactions.length} transaction{day.transactions.length !== 1 ? 's' : ''}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-bold text-gray-900">{formatCurrency(day.total)}</div>
                <div className="text-xs text-gray-500">
                  {expandedDay === day.date ? 'Click to collapse' : 'Click to expand'}
                </div>
              </div>
            </button>

            {/* Expanded Transactions */}
            {expandedDay === day.date && (
              <div className="border-t border-gray-200 bg-gray-50">
                {day.transactions.map((txn: any, index: number) => (
                  <button
                    key={index}
                    onClick={() => {
                      setSelectedTransaction({
                        id: txn.id,
                        merchant: txn.merchant,
                        category: txn.category,
                        amount: txn.amount,
                        description: txn.description,
                        date: day.date,
                        time: txn.time,
                        emoji: txn.emoji,
                      });
                      setIsModalOpen(true);
                    }}
                    className="w-full flex items-center justify-between px-4 py-3 border-b border-gray-100 last:border-0 hover:bg-white transition text-left"
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 text-xs font-medium">
                        {txn.merchant?.charAt(0)?.toUpperCase() || '?'}
                      </div>
                      <div>
                        <div className="font-medium text-gray-900 text-sm">{txn.merchant}</div>
                        <div className="text-xs text-gray-500 capitalize">{txn.category}</div>
                      </div>
                    </div>
                    <div className="text-right flex items-center gap-2">
                      <div>
                        <div className="font-semibold text-gray-900 text-sm">
                          {formatCurrency(txn.amount)}
                        </div>
                        {txn.time && (
                          <div className="text-xs text-gray-500">{txn.time}</div>
                        )}
                      </div>
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Transaction Edit Modal */}
      <TransactionDetailModal
        transaction={selectedTransaction}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedTransaction(null);
        }}
      />
    </div>
  );
}
