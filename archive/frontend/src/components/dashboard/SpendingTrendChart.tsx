'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from 'recharts';
import { getSpendingTrend } from '@/lib/api';

type ViewType = 'daily' | 'monthly' | 'yearly';

interface CategorySpend {
  category: string;
  amount: number;
}

interface TrendDataPoint {
  day: number;
  date: string;
  daily: number;
  cumulative: number;
  budget_pace: number;
  top_categories?: CategorySpend[];
}

interface LastMonthDataPoint {
  day: number;
  cumulative: number;
}

interface DailyTrendData {
  this_month: TrendDataPoint[];
  last_month: LastMonthDataPoint[];
  budget: number;
  current_total: number;
  projected_total: number;
  days_elapsed: number;
  days_in_month: number;
  on_track: boolean;
  month_name: string;
  last_month_name: string;
}

interface MultiViewDataPoint {
  period: string;
  short_label: string;
  amount: number;
  is_current: boolean;
  projected?: number;
  month?: number;
  year?: number;
}

interface MultiViewTrendData {
  view: 'monthly' | 'yearly';
  data: MultiViewDataPoint[];
  total: number;
  average: number;
  current: number;
  previous: number;
  budget: number;
  change: number;
  change_pct: number;
  period_label: string;
  current_year_projected?: number;
}

interface SpendingTrendProps {
  trend: DailyTrendData;
  userBudget?: number;
}

export function SpendingTrendChart({ trend: initialTrend, userBudget }: SpendingTrendProps) {
  const router = useRouter();
  const [view, setView] = useState<ViewType>('daily');
  const [trendData, setTrendData] = useState<DailyTrendData | MultiViewTrendData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use user's set budget if available
  const effectiveBudget = userBudget && userBudget > 0 ? userBudget : initialTrend.budget;

  // Fetch data when view changes
  useEffect(() => {
    if (view === 'daily') {
      setTrendData(null); // Use prop data for daily view
      setError(null);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getSpendingTrend(view, userBudget);
        setTrendData(data);
      } catch (err) {
        console.error('Failed to fetch spending trend:', err);
        setError('Failed to load data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [view, userBudget]);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);

  const formatCompactCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(1)}k`;
    }
    return `$${value.toFixed(0)}`;
  };

  // Render daily view (original implementation)
  const renderDailyView = () => {
    const trend = initialTrend;
    const budgetSource = userBudget && userBudget > 0 ? 'Your budget' : `Based on ${trend.last_month_name}`;

    // Recalculate projected and on_track based on effective budget
    const projectedTotal = trend.days_elapsed > 0
      ? (trend.current_total / trend.days_elapsed) * trend.days_in_month
      : 0;
    const isOnTrack = projectedTotal <= effectiveBudget;

    // Build chart data for full month (including future projection)
    const dailyRate = trend.days_elapsed > 0 ? trend.current_total / trend.days_elapsed : 0;
    const chartData: Array<{
      day: number;
      date: string;
      daily: number;
      cumulative: number | null;
      projected: number | null;
      budget_pace: number;
      top_categories: CategorySpend[];
      isToday: boolean;
    }> = [];

    for (let day = 1; day <= trend.days_in_month; day++) {
      const actualPoint = trend.this_month.find((p) => p.day === day);
      const isToday = day === trend.days_elapsed;
      const isFuture = day > trend.days_elapsed;

      if (isFuture) {
        // Future days: show projection only
        const projectedCumulative = trend.current_total + dailyRate * (day - trend.days_elapsed);
        chartData.push({
          day,
          date: `${trend.month_name} ${day}`,
          daily: 0,
          cumulative: null,
          projected: projectedCumulative,
          budget_pace: (effectiveBudget / trend.days_in_month) * day,
          top_categories: [],
          isToday: false,
        });
      } else {
        // Past/current days: show actual data
        chartData.push({
          day,
          date: actualPoint?.date || `${trend.month_name} ${day}`,
          daily: actualPoint?.daily || 0,
          cumulative: actualPoint?.cumulative || 0,
          projected: isToday ? (actualPoint?.cumulative ?? 0) : null, // Connect at today
          budget_pace: (effectiveBudget / trend.days_in_month) * day,
          top_categories: actualPoint?.top_categories || [],
          isToday,
        });
      }
    }

    // Calculate pace status
    const paceDiff = trend.current_total - (effectiveBudget / trend.days_in_month * trend.days_elapsed);
    const pacePercent = effectiveBudget > 0
      ? ((trend.current_total / (effectiveBudget / trend.days_in_month * trend.days_elapsed)) - 1) * 100
      : 0;

    return (
      <>
        {/* Key Metrics */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Spent</p>
            <p className="text-2xl font-bold" style={{ color: '#CA8A04' }}>
              {formatCurrency(trend.current_total)}
            </p>
            <p className="text-xs text-slate-500">
              Day {trend.days_elapsed} of {trend.days_in_month}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Budget</p>
            <p className="text-2xl font-bold" style={{ color: '#059669' }}>
              {formatCurrency(effectiveBudget)}
            </p>
            <p className="text-xs text-slate-500">
              {budgetSource}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Projected</p>
            <p className="text-2xl font-bold" style={{ color: isOnTrack ? '#059669' : '#DC2626' }}>
              {formatCurrency(projectedTotal)}
            </p>
            <p className="text-xs text-slate-500">
              {isOnTrack
                ? `${formatCurrency(effectiveBudget - projectedTotal)} under`
                : `${formatCurrency(projectedTotal - effectiveBudget)} over`}
            </p>
          </div>
        </div>

        {/* Chart */}
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 12, fill: '#64748B' }}
                tickLine={false}
                axisLine={{ stroke: '#E2E8F0' }}
                tickFormatter={(day) => (day % 5 === 0 || day === 1 ? `${day}` : '')}
              />
              <YAxis
                tick={{ fontSize: 12, fill: '#64748B' }}
                tickLine={false}
                axisLine={{ stroke: '#E2E8F0' }}
                tickFormatter={(value) => formatCompactCurrency(value)}
                width={50}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload || payload.length === 0) return null;
                  const dataPoint = chartData.find((d) => d.day === label);
                  const topCategories = dataPoint?.top_categories || [];
                  const dailySpend = dataPoint?.daily || 0;
                  const isFuture = label > trend.days_elapsed;
                  const isToday = label === trend.days_elapsed;
                  const projectedAmount = dataPoint?.projected || 0;

                  // Format date label
                  let dateLabel: string;
                  if (dataPoint?.date && dataPoint.date.includes('-')) {
                    dateLabel = new Date(dataPoint.date + 'T00:00:00').toLocaleDateString('en-US', {
                      weekday: 'short',
                      month: 'short',
                      day: 'numeric',
                    });
                  } else {
                    dateLabel = `${trend.month_name} ${label}`;
                  }

                  return (
                    <div
                      style={{
                        backgroundColor: '#FFFFFF',
                        border: '1px solid #E2E8F0',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px -1px rgba(15, 23, 42, 0.1)',
                        padding: '12px',
                        minWidth: '140px',
                      }}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <p className="text-xs font-semibold text-slate-600">{dateLabel}</p>
                        {isToday && (
                          <span className="text-[10px] font-medium text-sky-600 bg-sky-50 px-1.5 py-0.5 rounded">
                            Today
                          </span>
                        )}
                      </div>
                      {isFuture ? (
                        <div className="space-y-1">
                          <p className="text-xs text-slate-500">Projected cumulative</p>
                          <p className="text-sm font-semibold text-slate-900">
                            {formatCurrency(projectedAmount)}
                          </p>
                        </div>
                      ) : dailySpend > 0 ? (
                        <div className="space-y-1.5">
                          {topCategories.map((cat, idx) => (
                            <div key={idx} className="flex justify-between items-center gap-3">
                              <span className="text-xs text-slate-600 capitalize truncate max-w-[90px]">
                                {cat.category}
                              </span>
                              <span className="text-xs font-medium text-slate-900">
                                {formatCurrency(cat.amount)}
                              </span>
                            </div>
                          ))}
                          {topCategories.length > 0 && (
                            <div className="border-t border-slate-200 pt-1.5 mt-1.5">
                              <div className="flex justify-between items-center gap-3">
                                <span className="text-xs font-medium text-slate-600">Total</span>
                                <span className="text-xs font-semibold text-slate-900">
                                  {formatCurrency(dailySpend)}
                                </span>
                              </div>
                            </div>
                          )}
                          {topCategories.length === 0 && (
                            <p className="text-xs text-slate-500">{formatCurrency(dailySpend)}</p>
                          )}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-400">No spending</p>
                      )}
                    </div>
                  );
                }}
              />
              <Legend
                verticalAlign="top"
                height={36}
                formatter={(value) => {
                  const labels: Record<string, string> = {
                    cumulative: 'Actual',
                    projected: 'Projected',
                    budget_pace: 'Budget',
                  };
                  return <span className="text-sm text-slate-600">{labels[value] || value}</span>;
                }}
              />

              {/* Budget line (dashed gray) */}
              <Line
                type="monotone"
                dataKey="budget_pace"
                stroke="#94A3B8"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                activeDot={false}
              />

              {/* Actual spending (solid blue) */}
              <Line
                type="monotone"
                dataKey="cumulative"
                stroke="#0284C7"
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 6, strokeWidth: 2 }}
              />

              {/* Projected spending (dashed, from today onwards) */}
              <Line
                type="monotone"
                dataKey="projected"
                stroke="#0284C7"
                strokeWidth={2}
                strokeDasharray="6 4"
                dot={false}
                activeDot={false}
                connectNulls={false}
              />

              {/* Today marker */}
              <ReferenceLine
                x={trend.days_elapsed}
                stroke="#0284C7"
                strokeWidth={2}
                strokeDasharray="3 3"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Pace Indicator */}
        {Math.abs(pacePercent) > 5 && (
          <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
            isOnTrack ? 'bg-sage-500/10' : 'bg-rose-600/10'
          }`}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={isOnTrack
                  ? "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  : "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                }
              />
            </svg>
            <span className={`text-sm font-medium ${
              isOnTrack ? 'text-sage-700' : 'text-rose-700'
            }`}>
              {isOnTrack
                ? `${formatCurrency(Math.abs(paceDiff))} under budget pace`
                : `${formatCurrency(Math.abs(paceDiff))} over budget pace`
              }
            </span>
          </div>
        )}
      </>
    );
  };

  // Handle bar click to navigate to filtered transactions
  const handleBarClick = (dataPoint: MultiViewDataPoint) => {
    if (view === 'monthly' && dataPoint.month && dataPoint.year) {
      router.push(`/transactions?month=${dataPoint.month}&year=${dataPoint.year}`);
    }
  };

  // Render monthly or yearly view
  const renderMultiView = () => {
    const data = trendData as MultiViewTrendData;
    if (!data || !data.data) return null;

    const isPositiveChange = data.change >= 0;
    const changeColor = isPositiveChange ? '#DC2626' : '#059669'; // Red for increase (bad), green for decrease (good)

    return (
      <>
        {/* Key Metrics */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">
              {view === 'monthly' ? 'This Month' : 'This Year'}
            </p>
            <p className="text-2xl font-bold" style={{ color: '#CA8A04' }}>
              {formatCurrency(data.current)}
            </p>
            <p className="text-xs text-slate-500">
              {view === 'yearly' && data.current_year_projected
                ? `Projected: ${formatCurrency(data.current_year_projected)}`
                : data.period_label}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Average</p>
            <p className="text-2xl font-bold" style={{ color: '#059669' }}>
              {formatCurrency(data.average)}
            </p>
            <p className="text-xs text-slate-500">
              Per {view === 'monthly' ? 'month' : 'year'}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Change</p>
            <p className="text-2xl font-bold" style={{ color: changeColor }}>
              {isPositiveChange ? '+' : ''}{data.change_pct.toFixed(0)}%
            </p>
            <p className="text-xs text-slate-500">
              vs {view === 'monthly' ? 'last month' : 'last year'}
            </p>
          </div>
        </div>

        {/* Chart */}
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data.data}
              margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis
                dataKey="short_label"
                tick={{ fontSize: 11, fill: '#64748B' }}
                tickLine={false}
                axisLine={{ stroke: '#E2E8F0' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: '#64748B' }}
                tickLine={false}
                axisLine={{ stroke: '#E2E8F0' }}
                tickFormatter={(value) => formatCompactCurrency(value)}
                width={55}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E2E8F0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(15, 23, 42, 0.1)',
                }}
                formatter={(value: number, name: string) => [
                  formatCurrency(value),
                  name === 'amount' ? 'Spending' : 'Projected',
                ]}
                labelFormatter={(label) => {
                  const point = data.data.find(d => d.short_label === label);
                  return point?.period || label;
                }}
              />
              <Legend
                verticalAlign="top"
                height={36}
                formatter={(value) => {
                  const labels: Record<string, string> = {
                    amount: 'Spending',
                    projected: 'Projected (Current Year)',
                  };
                  return <span className="text-sm text-slate-600">{labels[value] || value}</span>;
                }}
              />

              {/* Spending bars */}
              <Bar
                dataKey="amount"
                fill="#0284C7"
                radius={[4, 4, 0, 0]}
                maxBarSize={50}
                onClick={(data) => handleBarClick(data)}
                style={{ cursor: view === 'monthly' ? 'pointer' : 'default' }}
              />

              {/* Average reference line */}
              <ReferenceLine
                y={data.average}
                stroke="#7C3AED"
                strokeDasharray="3 3"
                label={{
                  value: 'Avg',
                  position: 'right',
                  fill: '#7C3AED',
                  fontSize: 12,
                }}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Trend Summary */}
        <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
          !isPositiveChange ? 'bg-sage-500/10' : 'bg-rose-600/10'
        }`}>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d={!isPositiveChange
                ? "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                : "M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"
              }
            />
          </svg>
          <span className={`text-sm font-medium ${
            !isPositiveChange ? 'text-sage-700' : 'text-rose-700'
          }`}>
            {!isPositiveChange
              ? `Spending decreased by ${formatCurrency(Math.abs(data.change))} from ${view === 'monthly' ? 'last month' : 'last year'}`
              : `Spending increased by ${formatCurrency(Math.abs(data.change))} from ${view === 'monthly' ? 'last month' : 'last year'}`
            }
          </span>
        </div>
      </>
    );
  };

  // Determine status for header badge
  const getStatusBadge = () => {
    if (view === 'daily') {
      const projectedTotal = initialTrend.days_elapsed > 0
        ? (initialTrend.current_total / initialTrend.days_elapsed) * initialTrend.days_in_month
        : 0;
      const isOnTrack = projectedTotal <= effectiveBudget;
      return {
        isPositive: isOnTrack,
        text: isOnTrack ? 'On Track' : 'Over Pace',
      };
    } else if (trendData && 'change' in trendData) {
      const data = trendData as MultiViewTrendData;
      return {
        isPositive: data.change <= 0,
        text: data.change <= 0 ? 'Decreasing' : 'Increasing',
      };
    }
    return { isPositive: true, text: 'Loading' };
  };

  const status = getStatusBadge();

  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold tracking-tight text-slate-900">Spending Trend</h3>
          <p className="text-sm text-slate-500">
            {view === 'daily' && `${initialTrend.month_name} spending vs budget pace`}
            {view === 'monthly' && 'Monthly spending over the past year'}
            {view === 'yearly' && 'Yearly spending comparison'}
          </p>
        </div>

        {/* Status Badge */}
        {!loading && (
          <div className={`px-3 py-1.5 rounded text-xs font-semibold uppercase tracking-wide ${
            status.isPositive
              ? 'bg-sage-500/10 text-sage-700'
              : 'bg-rose-600/10 text-rose-700'
          }`}>
            {status.text}
          </div>
        )}
      </div>

      {/* View Toggle */}
      <div className="flex gap-1 p-1 bg-slate-100 rounded-lg mb-6 w-fit">
        {(['daily', 'monthly', 'yearly'] as ViewType[]).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
              view === v
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {v === 'daily' ? 'Day' : v === 'monthly' ? 'Month' : 'Year'}
          </button>
        ))}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="h-80 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-slate-500">Loading {view} data...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="h-80 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-center">
            <svg className="w-12 h-12 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-sm text-slate-500">{error}</p>
            <button
              onClick={() => setView('daily')}
              className="text-sm text-sky-600 hover:text-sky-700 font-medium"
            >
              Back to daily view
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      {!loading && !error && view === 'daily' && renderDailyView()}
      {!loading && !error && view !== 'daily' && trendData && renderMultiView()}
    </div>
  );
}
