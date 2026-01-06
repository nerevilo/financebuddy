'use client';

import { BarList } from '@tremor/react';
import { formatCurrency } from '@/lib/utils';

interface Merchant {
  merchant: string;
  total: number;
  count: number;
  percentage: number;
}

interface TopMerchantsProps {
  merchants: Merchant[];
}

export function TopMerchants({ merchants }: TopMerchantsProps) {
  const chartData = merchants.slice(0, 10).map((m) => ({
    name: m.merchant,
    value: m.total,
    count: m.count,
  }));

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Merchants</h3>

      <div className="space-y-3">
        {merchants.slice(0, 10).map((merchant, index) => (
          <div
            key={merchant.merchant}
            className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0"
          >
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-400 w-5">{index + 1}.</span>
              <div>
                <p className="text-sm font-medium text-gray-900">{merchant.merchant}</p>
                <p className="text-xs text-gray-500">{merchant.count} transactions</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold text-gray-900">
                {formatCurrency(merchant.total)}
              </p>
              <p className="text-xs text-gray-500">{merchant.percentage}%</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
