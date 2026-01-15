'use client';

interface SpendingVelocityProps {
  velocity: {
    spent_so_far: number;
    days_elapsed: number;
    days_in_month: number;
    time_progress: number;
    spending_progress: number;
    daily_average: number;
    projected_total: number;
    last_month_total: number;
    vs_last_month: number;
    vs_last_month_pct: number;
    on_track: boolean;
  };
}

export function SpendingVelocity({ velocity }: SpendingVelocityProps) {
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-neutral-200 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 mb-4">Spending Velocity</h3>

      <div className="space-y-4">
        {/* Amount spent */}
        <div>
          <div className="flex justify-between items-baseline mb-2">
            <span className="text-2xl font-bold text-neutral-900">
              {formatCurrency(velocity.spent_so_far)}
            </span>
            <span className="text-sm text-neutral-500">
              spent so far (Jan {velocity.days_elapsed})
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-neutral-200 rounded-full h-3 overflow-hidden">
            <div
              className={`h-full transition-all ${
                velocity.on_track ? 'bg-success-500' : 'bg-danger-500'
              }`}
              style={{ width: `${Math.min(velocity.spending_progress, 100)}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-xs text-neutral-500 mt-1">
            <span>{velocity.spending_progress.toFixed(0)}% of projected</span>
            <span>{velocity.time_progress.toFixed(0)}% of month elapsed</span>
          </div>
        </div>

        {/* Projections */}
        <div className="pt-3 border-t border-neutral-200 space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm text-neutral-600">On track to spend:</span>
            <span className="font-semibold text-neutral-900">
              {formatCurrency(velocity.projected_total)}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-sm text-neutral-600">Last month:</span>
            <span className="text-sm text-neutral-500">
              {formatCurrency(velocity.last_month_total)}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-sm text-neutral-600">Daily average:</span>
            <span className="text-sm font-medium text-neutral-700">
              {formatCurrency(velocity.daily_average)}
            </span>
          </div>

          {/* Comparison indicator */}
          {Math.abs(velocity.vs_last_month_pct) > 5 && (
            <div className={`text-sm p-2 rounded-lg flex items-center gap-2 ${
              velocity.vs_last_month > 0 ? 'bg-danger-50 text-danger-600' : 'bg-success-50 text-success-600'
            }`}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={velocity.vs_last_month > 0 ? "M5 15l7-7 7 7" : "M19 9l-7 7-7-7"} />
              </svg>
              {Math.abs(velocity.vs_last_month_pct).toFixed(0)}% vs last month
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
