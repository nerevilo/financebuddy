'use client';

interface TopMerchantsWidgetProps {
  merchants: Array<{
    merchant: string;
    total: number;
    visits: number;
    avg_per_visit: number;
    insight: string | null;
  }>;
}

export function TopMerchantsWidget({ merchants }: TopMerchantsWidgetProps) {
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-neutral-200 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 mb-4">Top Merchants</h3>

      <div className="space-y-4">
        {merchants.slice(0, 5).map((merchant, index) => (
          <div key={index} className="flex items-start justify-between pb-3 border-b border-neutral-100 last:border-0">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-neutral-400 text-sm font-medium">#{index + 1}</span>
                <span className="font-medium text-neutral-900">{merchant.merchant}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-neutral-500">
                <span>{formatCurrency(merchant.total)}</span>
                <span>•</span>
                <span>{merchant.visits} visits</span>
              </div>
              {merchant.insight && (
                <div className="mt-1 text-xs text-primary-600 font-medium">
                  {merchant.insight}
                </div>
              )}
            </div>
            <div className="text-right text-sm text-neutral-500">
              {formatCurrency(merchant.avg_per_visit)}/visit
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 text-center">
        <button className="text-sm text-primary-600 hover:text-primary-700 font-medium">
          View All →
        </button>
      </div>
    </div>
  );
}
