'use client';

interface RecentTransactionsWidgetProps {
  transactions: Array<{
    id: string;
    merchant: string;
    category: string;
    amount: number;
    date: string;
    description: string;
    emoji: string;
  }>;
}

export function RecentTransactionsWidget({ transactions }: RecentTransactionsWidgetProps) {
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Transactions</h3>

      <div className="space-y-3">
        {transactions.slice(0, 5).map((txn, index) => (
          <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
            <div className="flex items-center gap-3 flex-1">
              <span className="text-2xl">{txn.emoji}</span>
              <div>
                <div className="font-medium text-gray-900 text-sm">{txn.merchant}</div>
                <div className="text-xs text-gray-500">{formatDate(txn.date)}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="font-semibold text-gray-900 text-sm">
                {formatCurrency(txn.amount)}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 text-center">
        <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
          View All Transactions →
        </button>
      </div>
    </div>
  );
}
