'use client';

interface RecurringPayment {
  merchant: string;
  amount: number;
  frequency: 'weekly' | 'biweekly' | 'monthly' | 'yearly';
  category: string | null;
  last_date: string | null;
  next_expected: string | null;
  occurrences: number;
  emoji: string;
}

interface RecurringPaymentsWidgetProps {
  data: {
    recurring_payments: RecurringPayment[];
    total_monthly: number;
    count: number;
  };
}

const frequencyLabels: Record<string, string> = {
  weekly: 'Weekly',
  biweekly: 'Bi-weekly',
  monthly: 'Monthly',
  yearly: 'Yearly',
};

const frequencyColors: Record<string, string> = {
  weekly: 'bg-blue-100 text-blue-700',
  biweekly: 'bg-purple-100 text-purple-700',
  monthly: 'bg-green-100 text-green-700',
  yearly: 'bg-amber-100 text-amber-700',
};

export function RecurringPaymentsWidget({ data }: RecurringPaymentsWidgetProps) {
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getDaysUntil = (dateString: string | null) => {
    if (!dateString) return null;
    const date = new Date(dateString);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    date.setHours(0, 0, 0, 0);
    const diffTime = date.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  if (!data || data.recurring_payments.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-neutral-200 p-6">
        <h3 className="text-lg font-semibold text-neutral-900 mb-4">Recurring Payments</h3>
        <p className="text-neutral-500 text-sm">No recurring payments detected yet. Keep tracking your expenses!</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-neutral-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-neutral-900">Recurring Payments</h3>
        <div className="text-right">
          <p className="text-xs text-neutral-500 uppercase tracking-wide">Monthly Total</p>
          <p className="text-lg font-bold text-neutral-900">{formatCurrency(data.total_monthly)}</p>
        </div>
      </div>

      <div className="space-y-3">
        {data.recurring_payments.slice(0, 6).map((payment, index) => {
          const daysUntil = getDaysUntil(payment.next_expected);
          const isUpcoming = daysUntil !== null && daysUntil >= 0 && daysUntil <= 7;

          return (
            <div
              key={index}
              className={`flex items-center justify-between p-3 rounded-lg border ${
                isUpcoming ? 'border-amber-200 bg-amber-50' : 'border-neutral-100 bg-neutral-50'
              }`}
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <span className="text-xl">{payment.emoji}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="font-medium text-neutral-900 truncate">{payment.merchant}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${frequencyColors[payment.frequency]}`}>
                      {frequencyLabels[payment.frequency]}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-neutral-500">
                    {payment.category && <span>{payment.category}</span>}
                    {payment.category && payment.next_expected && <span>•</span>}
                    {payment.next_expected && (
                      <span className={isUpcoming ? 'text-amber-700 font-medium' : ''}>
                        Next: {formatDate(payment.next_expected)}
                        {daysUntil !== null && daysUntil >= 0 && (
                          <span className="ml-1">
                            ({daysUntil === 0 ? 'Today' : daysUntil === 1 ? 'Tomorrow' : `${daysUntil}d`})
                          </span>
                        )}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="text-right pl-3">
                <p className="font-semibold text-neutral-900">{formatCurrency(payment.amount)}</p>
              </div>
            </div>
          );
        })}
      </div>

      {data.count > 6 && (
        <div className="mt-4 text-center">
          <button className="text-sm text-primary-600 hover:text-primary-700 font-medium">
            View All {data.count} Recurring →
          </button>
        </div>
      )}
    </div>
  );
}
