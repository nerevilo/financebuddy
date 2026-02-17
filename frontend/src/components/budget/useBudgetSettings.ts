'use client';

import { useState, useEffect, useCallback } from 'react';
import { BudgetSettings } from './BudgetSettingModal';

const STORAGE_KEY = 'ledgi_budget_settings';

export function useBudgetSettings() {
  const [settings, setSettings] = useState<BudgetSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load settings from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setSettings(JSON.parse(stored));
      }
    } catch (error) {
      console.error('Failed to load budget settings:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Save settings to localStorage
  const saveSettings = useCallback((newSettings: BudgetSettings) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newSettings));
      setSettings(newSettings);
    } catch (error) {
      console.error('Failed to save budget settings:', error);
      throw error;
    }
  }, []);

  // Clear settings
  const clearSettings = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
      setSettings(null);
    } catch (error) {
      console.error('Failed to clear budget settings:', error);
    }
  }, []);

  // Get budget for a specific category
  const getCategoryBudget = useCallback((category: string): number | null => {
    if (!settings) return null;
    const found = settings.categoryBudgets.find(
      cb => cb.category.toLowerCase() === category.toLowerCase()
    );
    return found?.amount ?? null;
  }, [settings]);

  // Check if a category is over budget
  const isCategoryOverBudget = useCallback((category: string, spent: number): boolean => {
    const budget = getCategoryBudget(category);
    if (budget === null) return false;
    return spent > budget;
  }, [getCategoryBudget]);

  // Check if a category is near alert threshold
  const isCategoryNearLimit = useCallback((category: string, spent: number): boolean => {
    if (!settings) return false;
    const budget = getCategoryBudget(category);
    if (budget === null || budget === 0) return false;
    const percentUsed = (spent / budget) * 100;
    return percentUsed >= settings.alertThreshold && percentUsed < 100;
  }, [settings, getCategoryBudget]);

  return {
    settings,
    isLoading,
    saveSettings,
    clearSettings,
    getCategoryBudget,
    isCategoryOverBudget,
    isCategoryNearLimit,
    hasBudget: settings !== null && settings.totalMonthlyBudget > 0,
  };
}
