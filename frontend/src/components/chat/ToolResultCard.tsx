'use client';

import { formatCurrency } from '@/lib/utils';
import { Search, PieChart, TrendingUp, Target, Tag, AlertTriangle, BarChart3 } from 'lucide-react';
import type { ToolCall } from '@/lib/api';

interface ToolResultCardProps {
  toolCall: ToolCall;
}

export function ToolResultCard({ toolCall }: ToolResultCardProps) {
  const { name, result } = toolCall;

  if (!result || result.error) {
    return null;
  }

  // Render based on tool type
  switch (name) {
    case 'search_transactions':
      return <TransactionResults data={result} />;
    case 'get_spending_summary':
      return <SpendingSummary data={result} />;
    case 'get_spending_pace':
      return <SpendingPace data={result} />;
    case 'get_category_spending':
      return <CategorySpending data={result} />;
    case 'get_goals':
      return <GoalsList data={result} />;
    case 'update_transaction_tags':
      return <TagUpdateResult data={result} />;
    case 'get_unusual_transactions':
      return <UnusualTransactions data={result} />;
    case 'compare_periods':
      return <PeriodComparison data={result} />;
    default:
      return (
        <div className="bg-slate-50 rounded-lg p-2 text-xs border border-slate-200">
          <span className="text-slate-500">Tool: {name}</span>
        </div>
      );
  }
}

function TransactionResults({ data }: { data: any }) {
  if (!data.transactions?.length) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-3">
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <Search className="w-4 h-4" />
          <span>No transactions found</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
      <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
        <Search className="w-4 h-4 text-slate-500" />
        <span className="text-xs font-medium text-slate-600">
          {data.count} transaction{data.count !== 1 ? 's' : ''} found
        </span>
      </div>
      <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto">
        {data.transactions.slice(0, 5).map((tx: any) => (
          <div key={tx.id} className="px-3 py-2 flex justify-between items-center">
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-slate-800 truncate">
                {tx.emoji} {tx.merchant}
              </div>
              <div className="text-xs text-slate-500">
                {tx.date} &middot; {tx.category}
              </div>
            </div>
            <div className="text-sm font-semibold text-slate-900 ml-3">
              {formatCurrency(tx.amount)}
            </div>
          </div>
        ))}
      </div>
      {data.count > 5 && (
        <div className="px-3 py-2 bg-slate-50 border-t border-slate-200">
          <span className="text-xs text-slate-500">
            +{data.count - 5} more transactions
          </span>
        </div>
      )}
    </div>
  );
}

function SpendingSummary({ data }: { data: any }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-3">
      <div className="flex items-center gap-2 mb-2">
        <PieChart className="w-4 h-4 text-slate-500" />
        <span className="text-xs font-medium text-slate-600">
          Spending Summary ({data.period?.replace('_', ' ')})
        </span>
      </div>
      <div className="text-lg font-bold text-slate-900 mb-3">
        {formatCurrency(data.total_spent || 0)}
      </div>
      <div className="space-y-1.5">
        {data.categories?.slice(0, 5).map((cat: any) => (
          <div key={cat.category} className="flex justify-between items-center text-sm">
            <span className="text-slate-600 truncate">
              {cat.emoji} {cat.category}
            </span>
            <div className="flex items-center gap-2">
              <span className="font-medium text-slate-800">
                {formatCurrency(cat.amount)}
              </span>
              <span className="text-xs text-slate-400 w-12 text-right">
                {cat.percentage?.toFixed(0)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SpendingPace({ data }: { data: any }) {
  const isOnTrack = data.on_track;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-3">
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp className={`w-4 h-4 ${isOnTrack ? 'text-emerald-500' : 'text-amber-500'}`} />
        <span className={`text-sm font-medium ${isOnTrack ? 'text-emerald-600' : 'text-amber-600'}`}>
          {isOnTrack ? 'On Track' : 'Spending Fast'}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-slate-500 text-xs">Spent so far</div>
          <div className="font-semibold text-slate-800">
            {formatCurrency(data.spent_so_far || 0)}
          </div>
        </div>
        <div>
          <div className="text-slate-500 text-xs">Projected total</div>
          <div className="font-semibold text-slate-800">
            {formatCurrency(data.projected_total || 0)}
          </div>
        </div>
        <div>
          <div className="text-slate-500 text-xs">Daily average</div>
          <div className="font-semibold text-slate-800">
            {formatCurrency(data.daily_average || 0)}
          </div>
        </div>
        <div>
          <div className="text-slate-500 text-xs">vs Last month</div>
          <div className={`font-semibold ${(data.vs_last_month || 0) > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
            {(data.vs_last_month || 0) > 0 ? '+' : ''}{formatCurrency(data.vs_last_month || 0)}
          </div>
        </div>
      </div>
      {/* Progress bar */}
      <div className="mt-3">
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>Day {data.days_elapsed} of {data.days_in_month}</span>
          <span>{data.time_progress?.toFixed(0)}% of month</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${isOnTrack ? 'bg-emerald-500' : 'bg-amber-500'}`}
            style={{ width: `${Math.min(data.spending_progress || 0, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function CategorySpending({ data }: { data: any }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{data.emoji}</span>
        <div>
          <div className="text-sm font-medium text-slate-800 capitalize">{data.category}</div>
          <div className="text-xs text-slate-500">{data.period?.replace('_', ' ')}</div>
        </div>
      </div>
      <div className="text-lg font-bold text-slate-900 mb-3">
        {formatCurrency(data.total || 0)}
        <span className="text-xs font-normal text-slate-500 ml-2">
          ({data.transaction_count} transactions)
        </span>
      </div>
      {data.top_merchants?.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-xs font-medium text-slate-500">Top Merchants</div>
          {data.top_merchants.slice(0, 4).map((m: any, idx: number) => (
            <div key={idx} className="flex justify-between items-center text-sm">
              <span className="text-slate-600 truncate">{m.merchant}</span>
              <span className="font-medium text-slate-800">{formatCurrency(m.total)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function GoalsList({ data }: { data: any }) {
  if (!data.goals?.length) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-3">
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <Target className="w-4 h-4" />
          <span>No goals set yet</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
      <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
        <Target className="w-4 h-4 text-slate-500" />
        <span className="text-xs font-medium text-slate-600">
          {data.count} goal{data.count !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="divide-y divide-slate-100">
        {data.goals.map((goal: any) => (
          <div key={goal.id} className="px-3 py-2">
            <div className="flex justify-between items-center mb-1">
              <span className="font-medium text-slate-800 text-sm">{goal.name}</span>
              <span className="text-xs text-slate-600">{goal.progress_pct?.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5 mb-1">
              <div
                className="bg-emerald-500 h-1.5 rounded-full transition-all"
                style={{ width: `${Math.min(goal.progress_pct || 0, 100)}%` }}
              />
            </div>
            <div className="text-xs text-slate-500">
              {formatCurrency(goal.current)} of {formatCurrency(goal.target)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TagUpdateResult({ data }: { data: any }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-3">
      <div className="flex items-center gap-2 mb-2">
        <Tag className="w-4 h-4 text-emerald-500" />
        <span className="text-sm font-medium text-emerald-600">Tags Updated</span>
      </div>
      <div className="text-sm text-slate-600 mb-2">{data.merchant}</div>
      {data.changes?.length > 0 && (
        <div className="space-y-1">
          {data.changes.map((change: string, idx: number) => (
            <div key={idx} className="text-xs text-slate-500">{change}</div>
          ))}
        </div>
      )}
      {data.current_tags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {data.current_tags.map((tag: string) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-xs"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function UnusualTransactions({ data }: { data: any }) {
  if (!data.transactions?.length) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-3">
        <div className="flex items-center gap-2 text-emerald-600 text-sm">
          <AlertTriangle className="w-4 h-4" />
          <span>No unusual transactions detected</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
      <div className="px-3 py-2 bg-amber-50 border-b border-amber-200 flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-600" />
        <span className="text-xs font-medium text-amber-700">
          {data.count} unusual transaction{data.count !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="divide-y divide-slate-100">
        {data.transactions.map((tx: any) => (
          <div key={tx.id} className="px-3 py-2">
            <div className="flex justify-between items-center">
              <span className="font-medium text-slate-800 text-sm truncate">
                {tx.emoji} {tx.merchant}
              </span>
              <span className="font-semibold text-slate-900 text-sm">
                {formatCurrency(tx.amount)}
              </span>
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
              {tx.date} &middot; {tx.anomaly_reason?.replace('_', ' ')}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PeriodComparison({ data }: { data: any }) {
  const changeIsPositive = (data.total_change || 0) > 0;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-3">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-4 h-4 text-slate-500" />
        <span className="text-xs font-medium text-slate-600">
          {data.period1?.replace('_', ' ')} vs {data.period2?.replace('_', ' ')}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <div className="text-xs text-slate-500 capitalize">{data.period1?.replace('_', ' ')}</div>
          <div className="font-semibold text-slate-800">{formatCurrency(data.total_period1 || 0)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 capitalize">{data.period2?.replace('_', ' ')}</div>
          <div className="font-semibold text-slate-800">{formatCurrency(data.total_period2 || 0)}</div>
        </div>
      </div>
      <div className={`text-sm font-medium ${changeIsPositive ? 'text-rose-600' : 'text-emerald-600'}`}>
        {changeIsPositive ? '+' : ''}{formatCurrency(data.total_change || 0)}
        <span className="text-xs ml-1">
          ({changeIsPositive ? '+' : ''}{data.total_change_pct?.toFixed(1)}%)
        </span>
      </div>
      {data.categories?.length > 0 && (
        <div className="mt-3 space-y-1.5">
          <div className="text-xs font-medium text-slate-500">Biggest Changes</div>
          {data.categories.slice(0, 3).map((cat: any) => (
            <div key={cat.category} className="flex justify-between items-center text-xs">
              <span className="text-slate-600">{cat.emoji} {cat.category}</span>
              <span className={cat.change > 0 ? 'text-rose-600' : 'text-emerald-600'}>
                {cat.change > 0 ? '+' : ''}{formatCurrency(cat.change)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
