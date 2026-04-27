'use client';

import { useState } from 'react';
import { useGoals } from '@/lib/hooks';
import { Goal, GoalCreate, GoalUpdate } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { GoalSettingModal } from './GoalSettingModal';

export function GoalsWidget() {
  const { goals, isLoading, createGoal, updateGoal, deleteGoal, addProgress } = useGoals('active');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null);
  const [addingProgressTo, setAddingProgressTo] = useState<string | null>(null);
  const [progressAmount, setProgressAmount] = useState('');

  const handleSaveGoal = async (goalData: GoalCreate | GoalUpdate) => {
    if (editingGoal) {
      await updateGoal(editingGoal.id, goalData as GoalUpdate);
    } else {
      await createGoal(goalData as GoalCreate);
    }
  };

  const handleDeleteGoal = async () => {
    if (editingGoal) {
      await deleteGoal(editingGoal.id);
    }
  };

  const handleAddProgress = async (goalId: string) => {
    const amount = parseFloat(progressAmount);
    if (amount > 0) {
      await addProgress(goalId, amount);
      setAddingProgressTo(null);
      setProgressAmount('');
    }
  };

  const openNewGoal = () => {
    setEditingGoal(null);
    setIsModalOpen(true);
  };

  const openEditGoal = (goal: Goal) => {
    setEditingGoal(goal);
    setIsModalOpen(true);
  };

  // Soft wash priority colors
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-rose-700 bg-rose-600/10';
      case 'medium': return 'text-amber-700 bg-amber-500/10';
      case 'low': return 'text-emerald-700 bg-emerald-500/10';
      default: return 'text-slate-700 bg-slate-500/10';
    }
  };

  const getProgressColor = (percent: number, onTrack: boolean | null) => {
    if (percent >= 100) return 'bg-emerald-500';
    if (onTrack === false) return 'bg-rose-600';
    if (percent >= 75) return 'bg-emerald-500';
    if (percent >= 50) return 'bg-slate-700';
    return 'bg-slate-500';
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow border border-slate-200 p-6">
        <div className="animate-pulse">
          <div className="h-5 w-32 bg-slate-200 rounded mb-4"></div>
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="h-20 bg-slate-100 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-xl shadow border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            <h2 className="text-lg font-semibold tracking-tight text-slate-900">Financial Goals</h2>
          </div>
          <button
            onClick={openNewGoal}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-lg transition"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Goal
          </button>
        </div>

        {/* Goals List */}
        <div className="p-4">
          {goals.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-4 bg-slate-50 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <p className="text-slate-600 mb-2">No goals yet</p>
              <p className="text-sm text-slate-500 mb-4">Set financial goals to track your progress</p>
              <button
                onClick={openNewGoal}
                className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 hover:-translate-y-px transition-all shadow-button"
              >
                Create Your First Goal
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {goals.map((goal) => {
                const progressPercent = goal.progress_percentage || 0;
                const isComplete = goal.status === 'completed' || progressPercent >= 100;

                return (
                  <div
                    key={goal.id}
                    className={`p-4 rounded-lg border transition cursor-pointer hover:shadow-sm ${
                      isComplete
                        ? 'bg-emerald-500/10 border-emerald-200'
                        : 'bg-slate-50 border-slate-200 hover:border-slate-300'
                    }`}
                    onClick={() => openEditGoal(goal)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium text-slate-900 truncate">{goal.name}</h3>
                          <span className={`text-xs font-semibold uppercase tracking-wide px-2 py-0.5 rounded capitalize ${getPriorityColor(goal.priority)}`}>
                            {goal.priority}
                          </span>
                        </div>
                        {goal.description && (
                          <p className="text-sm text-slate-500 truncate">{goal.description}</p>
                        )}
                      </div>
                      <div className="text-right ml-4">
                        <p className="text-lg font-semibold text-slate-900">
                          {formatCurrency(goal.current_amount)}
                        </p>
                        <p className="text-xs text-slate-500">
                          of {formatCurrency(goal.target_amount)}
                        </p>
                      </div>
                    </div>

                    {/* Progress bar */}
                    <div className="mb-2">
                      <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${getProgressColor(progressPercent, goal.on_track)}`}
                          style={{ width: `${Math.min(100, progressPercent)}%` }}
                        />
                      </div>
                    </div>

                    {/* Meta info */}
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-3 text-slate-500">
                        <span>{progressPercent.toFixed(0)}% complete</span>
                        {goal.deadline && (
                          <span>
                            Due {new Date(goal.deadline).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                          </span>
                        )}
                        {goal.on_track !== null && (
                          <span className={goal.on_track ? 'text-emerald-600' : 'text-rose-600'}>
                            {goal.on_track ? 'On track' : 'Behind'}
                          </span>
                        )}
                      </div>

                      {/* Quick add progress */}
                      {!isComplete && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setAddingProgressTo(addingProgressTo === goal.id ? null : goal.id);
                          }}
                          className="text-slate-600 hover:text-slate-800 font-medium"
                        >
                          + Add Progress
                        </button>
                      )}
                    </div>

                    {/* Quick progress input */}
                    {addingProgressTo === goal.id && (
                      <div
                        className="mt-3 flex gap-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="relative flex-1">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                          <input
                            type="number"
                            value={progressAmount}
                            onChange={(e) => setProgressAmount(e.target.value)}
                            placeholder="0.00"
                            min="0"
                            step="0.01"
                            className="w-full pl-7 pr-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-transparent bg-white"
                            autoFocus
                          />
                        </div>
                        <button
                          onClick={() => handleAddProgress(goal.id)}
                          disabled={!progressAmount || parseFloat(progressAmount) <= 0}
                          className="px-3 py-1.5 bg-slate-900 text-white text-sm rounded-lg hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
                        >
                          Add
                        </button>
                        <button
                          onClick={() => {
                            setAddingProgressTo(null);
                            setProgressAmount('');
                          }}
                          className="px-3 py-1.5 text-slate-600 text-sm hover:bg-slate-200 rounded-lg transition"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Monthly allocation summary */}
          {goals.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-200">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600">Total monthly allocation</span>
                <span className="font-semibold text-slate-900">
                  {formatCurrency(
                    goals.reduce((sum, g) => sum + (g.monthly_allocation || 0), 0)
                  )}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Goal Modal */}
      <GoalSettingModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingGoal(null);
        }}
        onSave={handleSaveGoal}
        onDelete={editingGoal ? handleDeleteGoal : undefined}
        existingGoal={editingGoal}
      />
    </>
  );
}
