'use client';

import { useState } from 'react';
import { useGoalSuggestions, useGoals } from '@/lib/hooks';
import { GoalSuggestion } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

export function GoalSuggestionsCard() {
  const { suggestions, isLoading } = useGoalSuggestions();
  const { createGoal } = useGoals();
  const [adoptingSuggestion, setAdoptingSuggestion] = useState<string | null>(null);
  const [dismissedSuggestions, setDismissedSuggestions] = useState<Set<string>>(new Set());

  const handleAdoptSuggestion = async (suggestion: GoalSuggestion) => {
    setAdoptingSuggestion(suggestion.name);
    try {
      await createGoal({
        name: suggestion.name,
        target_amount: suggestion.target_amount,
        monthly_allocation: suggestion.monthly_allocation,
        priority: suggestion.priority,
      });
      // Mark as dismissed after adoption
      setDismissedSuggestions(prev => {
        const newSet = new Set(prev);
        newSet.add(suggestion.name);
        return newSet;
      });
    } catch (error) {
      console.error('Failed to adopt suggestion:', error);
    } finally {
      setAdoptingSuggestion(null);
    }
  };

  const handleDismiss = (suggestionName: string) => {
    setDismissedSuggestions(prev => {
      const newSet = new Set(prev);
      newSet.add(suggestionName);
      return newSet;
    });
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high':
        return (
          <svg className="w-4 h-4 text-danger-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      case 'medium':
        return (
          <svg className="w-4 h-4 text-warning-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  // Filter out dismissed suggestions
  const activeSuggestions = suggestions.filter(s => !dismissedSuggestions.has(s.name));

  if (isLoading) {
    return (
      <div className="bg-gradient-to-r from-primary-50 to-primary-100 rounded-xl border border-primary-200 p-6">
        <div className="animate-pulse">
          <div className="h-5 w-40 bg-primary-200 rounded mb-3"></div>
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="h-16 bg-white/50 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (activeSuggestions.length === 0) {
    return null; // Don't show card if no suggestions
  }

  return (
    <div className="bg-gradient-to-r from-primary-50 to-primary-100 rounded-xl border border-primary-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-primary-200/50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
            <svg className="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-neutral-900">AI-Suggested Goals</h3>
            <p className="text-xs text-neutral-500">Based on your spending patterns</p>
          </div>
        </div>
      </div>

      {/* Suggestions */}
      <div className="p-4 space-y-3">
        {activeSuggestions.map((suggestion, index) => (
          <div
            key={index}
            className="bg-white rounded-lg p-4 border border-neutral-200 shadow-sm"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5">
                {getPriorityIcon(suggestion.priority)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-medium text-neutral-900">{suggestion.name}</h4>
                    <p className="text-sm text-neutral-500 mt-0.5">{suggestion.reason}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-semibold text-neutral-900">
                      {formatCurrency(suggestion.target_amount)}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {formatCurrency(suggestion.monthly_allocation)}/mo
                    </p>
                  </div>
                </div>

                {suggestion.related_category && (
                  <span className="inline-block mt-2 text-xs px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600">
                    {suggestion.related_category}
                  </span>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2 mt-3">
                  <button
                    onClick={() => handleAdoptSuggestion(suggestion)}
                    disabled={adoptingSuggestion === suggestion.name}
                    className="flex-1 py-1.5 px-3 bg-primary-500 text-white text-sm font-medium rounded-lg hover:bg-primary-600 disabled:opacity-50 transition"
                  >
                    {adoptingSuggestion === suggestion.name ? 'Creating...' : 'Create Goal'}
                  </button>
                  <button
                    onClick={() => handleDismiss(suggestion.name)}
                    className="py-1.5 px-3 text-neutral-500 text-sm hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
