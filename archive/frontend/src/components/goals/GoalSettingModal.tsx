'use client';

import { useState, useEffect } from 'react';
import { Goal, GoalCreate, GoalUpdate } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

interface GoalSettingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (goal: GoalCreate | GoalUpdate) => Promise<void>;
  onDelete?: () => Promise<void>;
  existingGoal?: Goal | null;
}

export function GoalSettingModal({
  isOpen,
  onClose,
  onSave,
  onDelete,
  existingGoal,
}: GoalSettingModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [targetAmount, setTargetAmount] = useState('');
  const [currentAmount, setCurrentAmount] = useState('');
  const [deadline, setDeadline] = useState('');
  const [priority, setPriority] = useState<'high' | 'medium' | 'low'>('medium');
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Populate form when editing existing goal
  useEffect(() => {
    if (existingGoal) {
      setName(existingGoal.name);
      setDescription(existingGoal.description || '');
      setTargetAmount(existingGoal.target_amount.toString());
      setCurrentAmount(existingGoal.current_amount.toString());
      setDeadline(existingGoal.deadline || '');
      setPriority(existingGoal.priority);
    } else {
      // Reset form for new goal
      setName('');
      setDescription('');
      setTargetAmount('');
      setCurrentAmount('0');
      setDeadline('');
      setPriority('medium');
    }
    setError(null);
  }, [existingGoal, isOpen]);

  // Calculate monthly allocation based on deadline
  const calculateMonthlyAllocation = () => {
    if (!deadline || !targetAmount) return null;
    const target = parseFloat(targetAmount);
    const current = parseFloat(currentAmount) || 0;
    const remaining = target - current;

    const deadlineDate = new Date(deadline);
    const now = new Date();
    const monthsLeft = Math.max(1,
      (deadlineDate.getFullYear() - now.getFullYear()) * 12 +
      (deadlineDate.getMonth() - now.getMonth())
    );

    return remaining / monthsLeft;
  };

  const monthlyAllocation = calculateMonthlyAllocation();
  const progressPercent = targetAmount && currentAmount
    ? Math.min(100, (parseFloat(currentAmount) / parseFloat(targetAmount)) * 100)
    : 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !targetAmount) return;

    setIsSaving(true);
    setError(null);
    try {
      const goalData: GoalCreate | GoalUpdate = {
        name: name.trim(),
        description: description.trim() || undefined,
        target_amount: parseFloat(targetAmount),
        current_amount: parseFloat(currentAmount) || 0,
        deadline: deadline || undefined,
        priority,
        monthly_allocation: monthlyAllocation || undefined,
      };

      await onSave(goalData);
      onClose();
    } catch (err) {
      console.error('Failed to save goal:', err);
      setError(err instanceof Error ? err.message : 'Failed to save goal. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;

    setIsDeleting(true);
    try {
      await onDelete();
      onClose();
    } catch (error) {
      console.error('Failed to delete goal:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-lg w-full m-4 max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">
                {existingGoal ? 'Edit Goal' : 'Create New Goal'}
              </h2>
              <p className="text-sm text-slate-500">Set a financial target to work towards</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto max-h-[calc(90vh-180px)]">
          {/* Goal Name */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Goal Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Emergency Fund, Vacation, New Car"
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this goal for? (optional)"
              rows={2}
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition resize-none"
            />
          </div>

          {/* Target Amount */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Target Amount *
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">$</span>
              <input
                type="number"
                value={targetAmount}
                onChange={(e) => setTargetAmount(e.target.value)}
                placeholder="0.00"
                min="0"
                step="0.01"
                className="w-full pl-8 pr-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition"
                required
              />
            </div>
          </div>

          {/* Current Progress */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Current Progress
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">$</span>
              <input
                type="number"
                value={currentAmount}
                onChange={(e) => setCurrentAmount(e.target.value)}
                placeholder="0.00"
                min="0"
                step="0.01"
                className="w-full pl-8 pr-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition"
              />
            </div>
            {targetAmount && parseFloat(targetAmount) > 0 && (
              <div className="mt-2">
                <div className="flex justify-between text-xs text-slate-500 mb-1">
                  <span>{progressPercent.toFixed(0)}% complete</span>
                  <span>{formatCurrency(parseFloat(targetAmount) - (parseFloat(currentAmount) || 0))} remaining</span>
                </div>
                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-slate-700 rounded-full transition-all duration-300"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Deadline */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Target Date
            </label>
            <input
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              min={new Date().toISOString().split('T')[0]}
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition"
            />
            {monthlyAllocation && monthlyAllocation > 0 && (
              <p className="mt-1 text-sm text-slate-600">
                Save {formatCurrency(monthlyAllocation)}/month to reach your goal
              </p>
            )}
          </div>

          {/* Priority */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Priority
            </label>
            <div className="flex gap-2">
              {(['high', 'medium', 'low'] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPriority(p)}
                  className={`flex-1 py-2 px-4 rounded-lg border-2 font-medium capitalize transition ${
                    priority === p
                      ? p === 'high'
                        ? 'border-rose-400 bg-rose-50 text-rose-600'
                        : p === 'medium'
                        ? 'border-amber-400 bg-amber-50 text-amber-700'
                        : 'border-emerald-400 bg-emerald-50 text-emerald-600'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </form>

        {/* Error Message */}
        {error && (
          <div className="mx-6 mb-4 p-3 bg-rose-50 border border-rose-200 rounded-lg">
            <p className="text-sm text-rose-600">{error}</p>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-slate-200 bg-slate-50">
          {existingGoal && onDelete ? (
            <button
              type="button"
              onClick={handleDelete}
              disabled={isDeleting}
              className="px-4 py-2 text-rose-500 hover:text-rose-600 font-medium disabled:opacity-50 transition"
            >
              {isDeleting ? 'Deleting...' : 'Delete Goal'}
            </button>
          ) : (
            <div />
          )}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-600 hover:text-slate-800 font-medium transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isSaving || !name.trim() || !targetAmount}
              className="px-6 py-2 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-button"
            >
              {isSaving ? 'Saving...' : existingGoal ? 'Update Goal' : 'Create Goal'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
