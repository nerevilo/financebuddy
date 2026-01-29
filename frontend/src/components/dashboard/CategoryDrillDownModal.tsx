'use client';

import { useState } from 'react';
import { mutate } from 'swr';
import { useCategoryMerchants, useTransactionsList } from '@/lib/hooks';
import { TransactionDetailModal } from '@/components/transactions/TransactionDetailModal';

interface CategoryDrillDownModalProps {
  category: string;
  emoji: string;
  isOpen: boolean;
  onClose: () => void;
}

export function CategoryDrillDownModal({ category, emoji, isOpen, onClose }: CategoryDrillDownModalProps) {
  // SWR will use prefetched data if available (instant open)
  const { data, isLoading } = useCategoryMerchants(isOpen ? category : null);

  // Fetch transactions for this category
  const { data: transactionsData, isLoading: transactionsLoading, refresh: refreshTransactions } = useTransactionsList(
    isOpen ? { category, limit: 50, sort_by: 'date', sort_order: 'desc' } : undefined
  );

  // State for transaction editing
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'merchants' | 'transactions'>('merchants');

  if (!isOpen) return null;

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const handleTransactionUpdated = async () => {
    // Refresh transactions list
    await refreshTransactions();
    // Also invalidate dashboard and category data
    await Promise.all([
      mutate('dashboard'),
      mutate((key) => Array.isArray(key) && key[0] === 'category-merchants', undefined, { revalidate: true }),
    ]);
  };

  // Generate pie chart segments
  const generatePieSegments = (merchants: any[]) => {
    let currentAngle = 0;
    const radius = 80;
    const centerX = 100;
    const centerY = 100;

    // Pastel macaron colors for pie chart
    const colors = [
      '#A18AE8', '#6DB88A', '#F5CE4D', '#F07878', '#BBA7F2',
      '#FFB3B3', '#8ECCA6', '#FFD9BE', '#B3DEC2', '#D4C4F9'
    ];

    return merchants.slice(0, 10).map((merchant, index) => {
      const angle = (merchant.percentage / 100) * 360;
      const startAngle = currentAngle;
      const endAngle = currentAngle + angle;

      const startRad = (startAngle - 90) * (Math.PI / 180);
      const endRad = (endAngle - 90) * (Math.PI / 180);

      const x1 = centerX + radius * Math.cos(startRad);
      const y1 = centerY + radius * Math.sin(startRad);
      const x2 = centerX + radius * Math.cos(endRad);
      const y2 = centerY + radius * Math.sin(endRad);

      const largeArcFlag = angle > 180 ? 1 : 0;

      const pathData = [
        `M ${centerX} ${centerY}`,
        `L ${x1} ${y1}`,
        `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
        'Z'
      ].join(' ');

      currentAngle = endAngle;

      return {
        pathData,
        color: colors[index % colors.length],
        merchant: merchant.merchant,
        percentage: merchant.percentage,
        amount: merchant.amount
      };
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full m-4 max-h-[90vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-neutral-200">
          <div className="flex items-center gap-3">
            <span className="text-4xl">{emoji}</span>
            <div>
              <h2 className="text-2xl font-bold text-neutral-900 capitalize">{category}</h2>
              {data && (
                <p className="text-neutral-600 text-sm">
                  {activeTab === 'merchants' ? 'Breakdown by merchant' : 'Tap to edit transactions'}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-neutral-200">
          <button
            onClick={() => setActiveTab('merchants')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition ${
              activeTab === 'merchants'
                ? 'text-slate-900 border-b-2 border-slate-700'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            By Merchant
          </button>
          <button
            onClick={() => setActiveTab('transactions')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition ${
              activeTab === 'transactions'
                ? 'text-slate-900 border-b-2 border-slate-700'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            All Transactions ({transactionsData.total})
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-160px)]">
          {/* Merchants Tab */}
          {activeTab === 'merchants' && (
            <>
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-400"></div>
                </div>
              ) : data && data.merchants ? (
                <div className="space-y-6">
                  {/* Total */}
                  <div className="bg-slate-50 rounded-xl p-4">
                    <div className="text-sm text-neutral-600">Total {category} spending</div>
                    <div className="text-3xl font-bold text-neutral-900">{formatCurrency(data.total)}</div>
                  </div>

                  {/* Pie Chart and Legend */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Pie Chart */}
                    <div className="flex items-center justify-center">
                      <svg viewBox="0 0 200 200" className="w-full max-w-[200px]">
                        {generatePieSegments(data.merchants).map((segment, index) => (
                          <g key={index}>
                            <path
                              d={segment.pathData}
                              fill={segment.color}
                              className="hover:opacity-80 transition cursor-pointer"
                            >
                              <title>{`${segment.merchant}: ${segment.percentage.toFixed(1)}%`}</title>
                            </path>
                          </g>
                        ))}
                      </svg>
                    </div>

                    {/* Legend */}
                    <div className="space-y-2">
                      {generatePieSegments(data.merchants).map((segment, index) => (
                        <div key={index} className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            <div
                              className="w-4 h-4 rounded"
                              style={{ backgroundColor: segment.color }}
                            ></div>
                            <span className="font-medium text-neutral-700">{segment.merchant}</span>
                          </div>
                          <div className="text-right">
                            <div className="font-semibold text-neutral-900">{formatCurrency(segment.amount)}</div>
                            <div className="text-xs text-neutral-500">{segment.percentage.toFixed(1)}%</div>
                          </div>
                        </div>
                      ))}
                      {data.merchants.length > 10 && (
                        <div className="text-xs text-neutral-500 pt-2">
                          +{data.merchants.length - 10} more merchants
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Full List */}
                  <div>
                    <h3 className="font-semibold text-neutral-900 mb-3">All Merchants</h3>
                    <div className="space-y-2">
                      {data.merchants.map((merchant: any, index: number) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-cream-50 rounded-lg hover:bg-neutral-100 transition">
                          <div>
                            <div className="font-medium text-neutral-900">{merchant.merchant}</div>
                            <div className="text-xs text-neutral-500">{merchant.count} purchases</div>
                          </div>
                          <div className="text-right">
                            <div className="font-semibold text-neutral-900">{formatCurrency(merchant.amount)}</div>
                            <div className="text-xs text-neutral-500">{merchant.percentage.toFixed(1)}%</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-neutral-500">
                  No data available for this category
                </div>
              )}
            </>
          )}

          {/* Transactions Tab */}
          {activeTab === 'transactions' && (
            <>
              {transactionsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-400"></div>
                </div>
              ) : transactionsData.transactions.length > 0 ? (
                <div className="space-y-2">
                  {transactionsData.transactions.map((transaction) => (
                    <button
                      key={transaction.id}
                      onClick={() => setSelectedTransactionId(transaction.id)}
                      className="w-full flex items-center justify-between p-3 bg-cream-50 rounded-lg hover:bg-neutral-100 transition text-left"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="font-medium text-neutral-900 truncate">
                          {transaction.merchant_name || transaction.description}
                        </div>
                        <div className="text-xs text-neutral-500">
                          {formatDate(transaction.date)}
                          {transaction.merchant_name && transaction.description !== transaction.merchant_name && (
                            <span className="ml-2 truncate">{transaction.description}</span>
                          )}
                        </div>
                      </div>
                      <div className="text-right ml-3 flex-shrink-0">
                        <div className={`font-semibold ${transaction.amount < 0 ? 'text-neutral-900' : 'text-success-500'}`}>
                          {transaction.amount < 0 ? '-' : '+'}
                          {formatCurrency(Math.abs(transaction.amount))}
                        </div>
                        <div className="text-xs text-slate-500">tap to edit</div>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-neutral-500">
                  No transactions in this category
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Transaction Detail Modal */}
      <TransactionDetailModal
        transactionId={selectedTransactionId}
        isOpen={!!selectedTransactionId}
        onClose={() => setSelectedTransactionId(null)}
        onUpdated={handleTransactionUpdated}
      />
    </div>
  );
}
