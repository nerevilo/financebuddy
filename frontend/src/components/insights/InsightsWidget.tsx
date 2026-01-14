'use client';

import { useState } from 'react';
import { useDailyInsights } from '@/lib/hooks';
import { Insight } from '@/lib/api';
import { InsightModal } from './InsightModal';

interface InsightsWidgetProps {
  onCreateGoal?: () => void;
  onSetBudget?: () => void;
}

export function InsightsWidget({ onCreateGoal, onSetBudget }: InsightsWidgetProps) {
  const { insights, isLoading, submitFeedback, regenerate } = useDailyInsights();
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      await regenerate();
    } catch (error) {
      console.error('Failed to regenerate insights:', error);
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleFeedback = async (feedback: 'helpful' | 'acted_on' | 'dismissed') => {
    if (selectedInsight) {
      await submitFeedback(selectedInsight.id, feedback);
    }
  };

  // Get styling based on insight type
  const getCardStyles = (type: string) => {
    switch (type) {
      case 'alert':
        return {
          bg: 'bg-gradient-to-br from-red-50 to-orange-50',
          border: 'border-red-200 hover:border-red-300',
          iconBg: 'bg-red-100',
          iconColor: 'text-red-600',
          label: 'Alert',
          labelBg: 'bg-red-100 text-red-700',
        };
      case 'opportunity':
        return {
          bg: 'bg-gradient-to-br from-green-50 to-emerald-50',
          border: 'border-green-200 hover:border-green-300',
          iconBg: 'bg-green-100',
          iconColor: 'text-green-600',
          label: 'Opportunity',
          labelBg: 'bg-green-100 text-green-700',
        };
      case 'optimization':
        return {
          bg: 'bg-gradient-to-br from-blue-50 to-indigo-50',
          border: 'border-blue-200 hover:border-blue-300',
          iconBg: 'bg-blue-100',
          iconColor: 'text-blue-600',
          label: 'Optimization',
          labelBg: 'bg-blue-100 text-blue-700',
        };
      default:
        return {
          bg: 'bg-gray-50',
          border: 'border-gray-200',
          iconBg: 'bg-gray-100',
          iconColor: 'text-gray-600',
          label: 'Insight',
          labelBg: 'bg-gray-100 text-gray-700',
        };
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'alert':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      case 'opportunity':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'optimization':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        );
      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="animate-pulse">
          <div className="flex items-center justify-between mb-4">
            <div className="h-6 w-32 bg-gray-200 rounded"></div>
            <div className="h-4 w-20 bg-gray-100 rounded"></div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-gray-100 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center">
              <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">AI Insights</h2>
              <p className="text-xs text-gray-500">Your personalized financial guidance</p>
            </div>
          </div>
          <button
            onClick={handleRegenerate}
            disabled={isRegenerating}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-purple-600 hover:bg-purple-50 rounded-lg transition disabled:opacity-50"
          >
            <svg
              className={`w-4 h-4 ${isRegenerating ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {isRegenerating ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {/* Insights Grid */}
        <div className="p-4">
          {insights.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-4 bg-purple-50 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <p className="text-gray-600 mb-2">No insights available</p>
              <p className="text-sm text-gray-500 mb-4">
                Connect more accounts or wait for more transaction data
              </p>
              <button
                onClick={handleRegenerate}
                disabled={isRegenerating}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition disabled:opacity-50"
              >
                Generate Insights
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {insights.map((insight) => {
                const styles = getCardStyles(insight.type);
                const hasInteracted = insight.feedback !== 'none';

                return (
                  <button
                    key={insight.id}
                    onClick={() => setSelectedInsight(insight)}
                    className={`${styles.bg} ${styles.border} border-2 rounded-xl p-4 text-left transition-all hover:shadow-md cursor-pointer group relative overflow-hidden`}
                  >
                    {/* Read indicator */}
                    {!insight.is_read && (
                      <div className="absolute top-2 right-2 w-2 h-2 bg-purple-500 rounded-full" />
                    )}

                    {/* Type label */}
                    <div className="flex items-center gap-2 mb-3">
                      <div className={`w-8 h-8 rounded-full ${styles.iconBg} flex items-center justify-center ${styles.iconColor}`}>
                        {insight.emoji ? (
                          <span className="text-lg">{insight.emoji}</span>
                        ) : (
                          getTypeIcon(insight.type)
                        )}
                      </div>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${styles.labelBg}`}>
                        {styles.label}
                      </span>
                    </div>

                    {/* Title */}
                    <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2 group-hover:text-gray-700 transition">
                      {insight.title}
                    </h3>

                    {/* Description preview */}
                    <p className="text-sm text-gray-600 line-clamp-2">{insight.description}</p>

                    {/* Feedback indicator */}
                    {hasInteracted && (
                      <div className="mt-2 flex items-center gap-1 text-xs text-gray-500">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        {insight.feedback === 'helpful' && 'Marked helpful'}
                        {insight.feedback === 'acted_on' && 'Acting on it'}
                        {insight.feedback === 'dismissed' && 'Dismissed'}
                      </div>
                    )}

                    {/* Hover indicator */}
                    <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition">
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Insight Modal */}
      <InsightModal
        insight={selectedInsight}
        isOpen={selectedInsight !== null}
        onClose={() => setSelectedInsight(null)}
        onFeedback={handleFeedback}
        onCreateGoal={onCreateGoal}
        onSetBudget={onSetBudget}
      />
    </>
  );
}
