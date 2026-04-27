'use client';

import { useState } from 'react';
import { Insight } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

interface InsightModalProps {
  insight: Insight | null;
  isOpen: boolean;
  onClose: () => void;
  onFeedback: (feedback: 'helpful' | 'acted_on' | 'dismissed') => Promise<void>;
  onCreateGoal?: () => void;
  onSetBudget?: () => void;
}

export function InsightModal({
  insight,
  isOpen,
  onClose,
  onFeedback,
  onCreateGoal,
  onSetBudget,
}: InsightModalProps) {
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  if (!isOpen || !insight) return null;

  const handleFeedback = async (feedback: 'helpful' | 'acted_on' | 'dismissed') => {
    setIsSubmittingFeedback(true);
    try {
      await onFeedback(feedback);
      setFeedbackSubmitted(true);
      // Auto-close after feedback
      setTimeout(() => {
        onClose();
        setFeedbackSubmitted(false);
      }, 1500);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  // Get styling based on insight type
  const getTypeStyles = () => {
    switch (insight.type) {
      case 'alert':
        return {
          bg: 'bg-danger-50',
          border: 'border-danger-200',
          iconBg: 'bg-danger-100',
          iconColor: 'text-danger-500',
          headerBg: 'bg-gradient-to-r from-secondary-500 to-secondary-500',
          accentColor: 'text-danger-500',
          buttonBg: 'bg-danger-500 hover:bg-danger-600',
        };
      case 'opportunity':
        return {
          bg: 'bg-success-50',
          border: 'border-success-200',
          iconBg: 'bg-success-100',
          iconColor: 'text-success-500',
          headerBg: 'bg-gradient-to-r from-success-500 to-success-500',
          accentColor: 'text-success-500',
          buttonBg: 'bg-success-500 hover:bg-success-600',
        };
      case 'optimization':
        return {
          bg: 'bg-primary-50',
          border: 'border-primary-200',
          iconBg: 'bg-primary-100',
          iconColor: 'text-primary-600',
          headerBg: 'bg-gradient-to-r from-primary-500 to-primary-500',
          accentColor: 'text-primary-600',
          buttonBg: 'bg-primary-500 hover:bg-primary-600',
        };
      default:
        return {
          bg: 'bg-cream-50',
          border: 'border-neutral-200',
          iconBg: 'bg-neutral-100',
          iconColor: 'text-neutral-600',
          headerBg: 'bg-gradient-to-r from-neutral-400 to-neutral-500',
          accentColor: 'text-neutral-600',
          buttonBg: 'bg-neutral-500 hover:bg-neutral-600',
        };
    }
  };

  const getTypeIcon = () => {
    switch (insight.type) {
      case 'alert':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      case 'opportunity':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'optimization':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        );
      default:
        return null;
    }
  };

  const getTypeLabel = () => {
    switch (insight.type) {
      case 'alert': return 'Alert';
      case 'opportunity': return 'Opportunity';
      case 'optimization': return 'Optimization';
      default: return 'Insight';
    }
  };

  const styles = getTypeStyles();

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-lg w-full m-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`${styles.headerBg} px-6 py-5 text-white`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                {insight.emoji ? (
                  <span className="text-2xl">{insight.emoji}</span>
                ) : (
                  getTypeIcon()
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-white/80 uppercase tracking-wide">
                  {getTypeLabel()}
                </p>
                <h2 className="text-xl font-bold">{insight.title}</h2>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white/70 hover:text-white transition"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Description */}
          <div>
            <p className="text-neutral-700 leading-relaxed">{insight.description}</p>
          </div>

          {/* Amount referenced */}
          {insight.amount_referenced && (
            <div className={`${styles.bg} rounded-xl p-4 border ${styles.border}`}>
              <p className="text-sm text-neutral-500 mb-1">Amount</p>
              <p className={`text-2xl font-bold ${styles.accentColor}`}>
                {formatCurrency(insight.amount_referenced)}
              </p>
              {insight.comparison_period && (
                <p className="text-sm text-neutral-500 mt-1">{insight.comparison_period}</p>
              )}
            </div>
          )}

          {/* Category */}
          {insight.category && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-neutral-500">Category:</span>
              <span className="px-3 py-1 bg-neutral-100 rounded-full text-sm font-medium text-neutral-700">
                {insight.category}
              </span>
            </div>
          )}

          {/* Action suggestion */}
          {insight.action && (
            <div className="bg-cream-50 rounded-xl p-4 border border-neutral-200">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-neutral-200 flex items-center justify-center shrink-0 mt-0.5">
                  <svg className="w-4 h-4 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-900 mb-1">Suggested Action</p>
                  <p className="text-neutral-600">{insight.action}</p>
                </div>
              </div>
            </div>
          )}

          {/* Quick actions based on type */}
          <div className="flex gap-3">
            {insight.type === 'opportunity' && onCreateGoal && (
              <button
                onClick={() => {
                  onCreateGoal();
                  onClose();
                }}
                className="flex-1 py-2.5 px-4 bg-success-500 text-white rounded-lg font-medium hover:bg-success-600 transition flex items-center justify-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                Create Savings Goal
              </button>
            )}
            {(insight.type === 'alert' || insight.type === 'optimization') && onSetBudget && (
              <button
                onClick={() => {
                  onSetBudget();
                  onClose();
                }}
                className={`flex-1 py-2.5 px-4 ${styles.buttonBg} text-white rounded-lg font-medium transition flex items-center justify-center gap-2`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                {insight.type === 'alert' ? 'Set Category Budget' : 'Adjust Budget'}
              </button>
            )}
          </div>
        </div>

        {/* Feedback section */}
        <div className="px-6 py-4 bg-cream-50 border-t border-neutral-200">
          {feedbackSubmitted ? (
            <div className="flex items-center justify-center gap-2 text-success-500">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="font-medium">Thanks for your feedback!</span>
            </div>
          ) : insight.feedback === 'none' ? (
            <div>
              <p className="text-sm text-neutral-600 text-center mb-3">Was this insight helpful?</p>
              <div className="flex justify-center gap-2">
                <button
                  onClick={() => handleFeedback('helpful')}
                  disabled={isSubmittingFeedback}
                  className="px-4 py-2 bg-white border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-cream-50 disabled:opacity-50 transition flex items-center gap-2"
                >
                  <svg className="w-4 h-4 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                  </svg>
                  Helpful
                </button>
                <button
                  onClick={() => handleFeedback('acted_on')}
                  disabled={isSubmittingFeedback}
                  className="px-4 py-2 bg-white border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-cream-50 disabled:opacity-50 transition flex items-center gap-2"
                >
                  <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  I'll act on it
                </button>
                <button
                  onClick={() => handleFeedback('dismissed')}
                  disabled={isSubmittingFeedback}
                  className="px-4 py-2 bg-white border border-neutral-200 rounded-lg text-sm font-medium text-neutral-500 hover:bg-cream-50 disabled:opacity-50 transition"
                >
                  Dismiss
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-neutral-500 text-center">
              You marked this as "{insight.feedback}"
            </p>
          )}
        </div>

        {/* Meta info */}
        <div className="px-6 py-3 bg-neutral-100 border-t border-neutral-200 text-xs text-neutral-500 text-center">
          Generated {new Date(insight.generated_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
          })}
        </div>
      </div>
    </div>
  );
}
