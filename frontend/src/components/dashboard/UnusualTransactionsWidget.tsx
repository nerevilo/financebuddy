'use client';

import { useState } from 'react';

interface UnusualTransaction {
  id: string;
  amount: number;
  merchant: string | null;
  category: string | null;
  date: string;
  anomaly_score: number;
  anomaly_reason: string;
  description: string;
  is_one_time: boolean;
  user_reviewed: boolean;
}

interface UnusualTransactionsWidgetProps {
  transactions: UnusualTransaction[];
  totalUnreviewed: number;
  onMarkOneTime: (id: string) => Promise<void>;
  onMarkNormal: (id: string) => Promise<void>;
  onRefresh?: () => void;
}

export function UnusualTransactionsWidget({
  transactions,
  totalUnreviewed,
  onMarkOneTime,
  onMarkNormal,
  onRefresh
}: UnusualTransactionsWidgetProps) {
  const [processingId, setProcessingId] = useState<string | null>(null);

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  const getReasonEmoji = (reason: string) => {
    const emojis: Record<string, string> = {
      'z_score': '📊',
      'iqr_outlier': '📈',
      'category_spike': '🔺',
      'new_large_merchant': '🆕',
    };
    return emojis[reason] || '⚠️';
  };

  const getReasonLabel = (reason: string) => {
    const labels: Record<string, string> = {
      'z_score': 'Unusually high',
      'iqr_outlier': 'Statistical outlier',
      'category_spike': 'Category spike',
      'new_large_merchant': 'New merchant',
    };
    return labels[reason] || 'Unusual';
  };

  const handleMarkOneTime = async (id: string) => {
    setProcessingId(id);
    try {
      await onMarkOneTime(id);
      onRefresh?.();
    } finally {
      setProcessingId(null);
    }
  };

  const handleMarkNormal = async (id: string) => {
    setProcessingId(id);
    try {
      await onMarkNormal(id);
      onRefresh?.();
    } finally {
      setProcessingId(null);
    }
  };

  if (!transactions.length) {
    return null;
  }

  return (
    <div className="bg-amber-50 rounded-xl shadow-sm border border-amber-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">⚠️</span>
          <h3 className="text-lg font-semibold text-gray-900">Unusual Transactions</h3>
          {totalUnreviewed > 0 && (
            <span className="bg-amber-500 text-white text-xs font-medium px-2 py-0.5 rounded-full">
              {totalUnreviewed} to review
            </span>
          )}
        </div>
      </div>

      <p className="text-sm text-gray-600 mb-4">
        These transactions look different from your usual spending. Mark them as one-time expenses to keep your budget accurate.
      </p>

      <div className="space-y-3">
        {transactions.map((txn) => (
          <div
            key={txn.id}
            className="bg-white rounded-lg border border-amber-100 p-4 transition-all hover:border-amber-300"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-base">{getReasonEmoji(txn.anomaly_reason)}</span>
                  <span className="font-semibold text-gray-900 truncate">
                    {txn.merchant || 'Unknown Merchant'}
                  </span>
                  <span className="text-xs text-gray-400">{formatDate(txn.date)}</span>
                </div>
                <p className="text-sm text-gray-600 line-clamp-2">{txn.description}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                    {getReasonLabel(txn.anomaly_reason)}
                  </span>
                  {txn.category && (
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      {txn.category}
                    </span>
                  )}
                </div>
              </div>

              <div className="text-right flex-shrink-0">
                <div className="text-lg font-bold text-gray-900 mb-2">
                  {formatCurrency(txn.amount)}
                </div>

                <div className="flex flex-col gap-1">
                  <button
                    onClick={() => handleMarkOneTime(txn.id)}
                    disabled={processingId === txn.id}
                    className="text-xs bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg transition disabled:opacity-50"
                  >
                    {processingId === txn.id ? '...' : 'One-Time'}
                  </button>
                  <button
                    onClick={() => handleMarkNormal(txn.id)}
                    disabled={processingId === txn.id}
                    className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-lg transition disabled:opacity-50"
                  >
                    Normal
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {totalUnreviewed > transactions.length && (
        <button className="mt-4 text-sm text-amber-700 hover:text-amber-800 font-medium">
          View all {totalUnreviewed} unusual transactions →
        </button>
      )}
    </div>
  );
}
