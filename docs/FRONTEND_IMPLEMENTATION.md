# Frontend Implementation Guide

## Overview

This document outlines what needs to be built in the Next.js frontend to display the new insights, goals, and profile features.

---

## New Pages/Routes

### 1. `/insights` - Daily Insights Page (or integrate into dashboard)

Display the 3 daily AI-generated insights with feedback buttons.

### 2. `/goals` - Goals Management Page

List, create, edit, and track financial goals.

### 3. `/settings` or `/profile` - User Profile/Settings Page

Update context notes, household size, income sources.

---

## Components to Build

### 1. `InsightsPanel` - Main insights display

**Location:** `src/components/insights/InsightsPanel.tsx`

**Purpose:** Fetch and display the 3 daily insights

**API Call:**
```typescript
const { data, error } = useSWR('/api/insights/daily', fetcher);
```

**Props:**
```typescript
interface Insight {
  id: string;
  type: 'alert' | 'opportunity' | 'optimization';
  title: string;
  description: string;
  action: string;
  emoji: string;
  category: string | null;
  amount_referenced: number | null;
  priority_score: number;
  feedback: 'none' | 'helpful' | 'acted_on' | 'dismissed';
  is_read: boolean;
  generated_at: string;
}

interface DailyInsightsResponse {
  date: string;
  insights: Insight[];
  generation_source: string;
  total_cost: number;
}
```

**UI Elements:**
- 3 insight cards stacked vertically or in a grid
- Each card shows: emoji, title, description, action button
- Feedback buttons: "Helpful" / "I did this" / "Dismiss"
- Visual distinction by type (alert=red/orange, opportunity=green, optimization=blue)

**Suggested Libraries:**
- Existing Radix UI components
- Lucide icons for feedback buttons (ThumbsUp, Check, X)

---

### 2. `InsightCard` - Individual insight card

**Location:** `src/components/insights/InsightCard.tsx`

**Purpose:** Display a single insight with feedback actions

**Props:**
```typescript
interface InsightCardProps {
  insight: Insight;
  onFeedback: (id: string, feedback: string) => void;
}
```

**Design:**
```
┌─────────────────────────────────────────────┐
│ 🚨  Spending is trending high!              │
│                                             │
│ At your current pace, you're projected to   │
│ spend $6152 this month...                   │
│                                             │
│ 👉 Review your spending from the past week  │
│                                             │
│ [Helpful] [I did this] [Dismiss]            │
└─────────────────────────────────────────────┘
```

**Styling by Type:**
```typescript
const typeStyles = {
  alert: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    border: 'border-red-200 dark:border-red-800',
    icon: 'text-red-500'
  },
  opportunity: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    border: 'border-green-200 dark:border-green-800',
    icon: 'text-green-500'
  },
  optimization: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    icon: 'text-blue-500'
  }
};
```

---

### 3. `GoalsList` - Goals list with progress

**Location:** `src/components/goals/GoalsList.tsx`

**Purpose:** Display all goals with progress bars

**API Call:**
```typescript
const { data: goals } = useSWR('/api/goals', fetcher);
```

**Props:**
```typescript
interface Goal {
  id: string;
  name: string;
  description: string | null;
  target_amount: number;
  current_amount: number;
  monthly_allocation: number | null;
  deadline: string | null;
  priority: 'high' | 'medium' | 'low';
  status: 'active' | 'completed' | 'paused';
  progress_percentage: number;
  months_to_goal: number | null;
  on_track: boolean | null;
}
```

**UI Elements:**
- List of goal cards
- Progress bar showing current/target
- "On track" / "Behind" indicator
- Add new goal button
- Edit/delete actions

---

### 4. `GoalCard` - Individual goal card

**Location:** `src/components/goals/GoalCard.tsx`

**Design:**
```
┌─────────────────────────────────────────────┐
│ 🎯 Honeymoon Fund                    [Edit] │
│                                             │
│ $1,000 / $6,000                       16.7% │
│ [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░]      │
│                                             │
│ 📅 Due: May 1, 2026 (4 months)             │
│ 💰 Monthly: $1,250                          │
│ ✅ On track                                 │
│                                             │
│ [+ Add Progress]                            │
└─────────────────────────────────────────────┘
```

---

### 5. `GoalForm` - Create/edit goal modal

**Location:** `src/components/goals/GoalForm.tsx`

**Fields:**
- Name (required)
- Description (optional)
- Target amount (required)
- Current amount (optional, default 0)
- Deadline (optional - if set, auto-calculates monthly allocation)
- Priority (high/medium/low)

**API Calls:**
```typescript
// Create
POST /api/goals/
{ name, target_amount, deadline, priority }

// Update
PATCH /api/goals/{id}
{ name, target_amount, current_amount, ... }

// Add progress
POST /api/goals/{id}/progress?amount=500
```

---

### 6. `GoalSuggestions` - Auto-suggested goals

**Location:** `src/components/goals/GoalSuggestions.tsx`

**Purpose:** Show system-suggested goals based on spending patterns

**API Call:**
```typescript
const { data: suggestions } = useSWR('/api/goals/suggestions', fetcher);
```

**UI:** Banner or cards showing suggestions with "Accept" button

---

### 7. `ProfileSettings` - User profile form

**Location:** `src/components/settings/ProfileSettings.tsx`

**Purpose:** Update user context for better insights

**API Calls:**
```typescript
// Get profile
GET /api/profile/

// Update profile
PATCH /api/profile/
{
  household_size: 2,
  location_city: "Ann Arbor",
  location_state: "MI",
  context_notes: "Saving for honeymoon. Husband is a student."
}
```

**Fields:**
- Household size (number input)
- City (text input)
- State (dropdown or text)
- Context notes (textarea) - explain your situation for better insights
- Insight frequency (daily/weekly toggle)

---

### 8. `IncomeManager` - Income sources management

**Location:** `src/components/settings/IncomeManager.tsx`

**Purpose:** View, add, and manage income sources

**API Calls:**
```typescript
// Get summary
GET /api/income/

// Auto-detect
POST /api/income/detect

// Create manual
POST /api/income/
{ name: "Salary", amount: 2510, frequency: "biweekly" }

// Delete
DELETE /api/income/{id}
```

**UI Elements:**
- Total monthly income display
- List of income sources
- "Detect Income" button
- "Add Manual Income" form

---

## Data Fetching Hooks

Add these to `src/lib/hooks.ts`:

```typescript
import useSWR from 'swr';
import { fetchAPI } from './api';

// Insights
export function useDailyInsights() {
  return useSWR('/api/insights/daily', fetchAPI);
}

export function useInsightHistory(limit = 30) {
  return useSWR(`/api/insights/history?limit=${limit}`, fetchAPI);
}

// Goals
export function useGoals(status?: string) {
  const url = status ? `/api/goals?status=${status}` : '/api/goals';
  return useSWR(url, fetchAPI);
}

export function useGoalSuggestions() {
  return useSWR('/api/goals/suggestions', fetchAPI);
}

// Profile
export function useProfile() {
  return useSWR('/api/profile', fetchAPI);
}

// Income
export function useIncome() {
  return useSWR('/api/income', fetchAPI);
}
```

---

## API Functions

Add these to `src/lib/api.ts`:

```typescript
// Insights
export async function submitInsightFeedback(
  insightId: string,
  feedback: 'helpful' | 'acted_on' | 'dismissed'
) {
  return fetchAPI(`/api/insights/${insightId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ feedback })
  });
}

export async function regenerateInsights() {
  return fetchAPI('/api/insights/regenerate', { method: 'POST' });
}

// Goals
export async function createGoal(goal: GoalCreate) {
  return fetchAPI('/api/goals', {
    method: 'POST',
    body: JSON.stringify(goal)
  });
}

export async function updateGoal(id: string, updates: Partial<Goal>) {
  return fetchAPI(`/api/goals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates)
  });
}

export async function addGoalProgress(id: string, amount: number) {
  return fetchAPI(`/api/goals/${id}/progress?amount=${amount}`, {
    method: 'POST'
  });
}

export async function deleteGoal(id: string) {
  return fetchAPI(`/api/goals/${id}`, { method: 'DELETE' });
}

// Profile
export async function updateProfile(updates: ProfileUpdate) {
  return fetchAPI('/api/profile', {
    method: 'PATCH',
    body: JSON.stringify(updates)
  });
}

// Income
export async function detectIncome() {
  return fetchAPI('/api/income/detect', { method: 'POST' });
}

export async function createIncomeSource(source: IncomeSourceCreate) {
  return fetchAPI('/api/income', {
    method: 'POST',
    body: JSON.stringify(source)
  });
}

export async function deleteIncomeSource(id: string) {
  return fetchAPI(`/api/income/${id}`, { method: 'DELETE' });
}
```

---

## TypeScript Types

Add to `src/types/index.ts` or similar:

```typescript
// Insights
export type InsightType = 'alert' | 'opportunity' | 'optimization';
export type InsightFeedback = 'none' | 'helpful' | 'acted_on' | 'dismissed';

export interface Insight {
  id: string;
  type: InsightType;
  title: string;
  description: string;
  action: string | null;
  emoji: string | null;
  category: string | null;
  amount_referenced: number | null;
  priority_score: number;
  feedback: InsightFeedback;
  feedback_at: string | null;
  generated_at: string;
  is_read: boolean;
  expires_at: string | null;
}

export interface DailyInsightsResponse {
  date: string;
  insights: Insight[];
  generation_source: string;
  total_cost: number;
}

// Goals
export type GoalPriority = 'high' | 'medium' | 'low';
export type GoalStatus = 'active' | 'completed' | 'paused' | 'cancelled';

export interface Goal {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  target_amount: number;
  current_amount: number;
  monthly_allocation: number | null;
  deadline: string | null;
  priority: GoalPriority;
  status: GoalStatus;
  auto_suggested: boolean;
  suggestion_reason: string | null;
  related_category: string | null;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
  progress_percentage: number | null;
  months_to_goal: number | null;
  on_track: boolean | null;
}

export interface GoalCreate {
  name: string;
  description?: string;
  target_amount: number;
  current_amount?: number;
  monthly_allocation?: number;
  deadline?: string;
  priority?: GoalPriority;
}

export interface GoalSuggestion {
  name: string;
  target_amount: number;
  monthly_allocation: number;
  reason: string;
  related_category: string | null;
  priority: GoalPriority;
}

// Profile
export interface UserProfile {
  id: string;
  user_id: string;
  monthly_income_estimate: number | null;
  income_last_calculated: string | null;
  household_size: number;
  location_city: string | null;
  location_state: string | null;
  context_notes: string | null;
  insight_frequency: string;
  preferred_categories: string[] | null;
  created_at: string;
  updated_at: string | null;
}

export interface ProfileUpdate {
  household_size?: number;
  location_city?: string;
  location_state?: string;
  context_notes?: string;
  insight_frequency?: string;
  preferred_categories?: string[];
}

// Income
export type IncomeFrequency = 'weekly' | 'biweekly' | 'monthly' | 'yearly' | 'irregular';

export interface IncomeSource {
  id: string;
  user_id: string;
  name: string;
  amount: number;
  frequency: IncomeFrequency;
  auto_detected: boolean;
  detection_pattern: string | null;
  next_expected_date: string | null;
  last_received_date: string | null;
  is_active: boolean;
  created_at: string;
}

export interface IncomeSummary {
  total_monthly_income: number;
  income_sources: IncomeSource[];
  auto_detected_count: number;
  manual_count: number;
}

export interface IncomeSourceCreate {
  name: string;
  amount: number;
  frequency: IncomeFrequency;
  next_expected_date?: string;
}

export interface DetectedIncome {
  name: string;
  amount: number;
  frequency: IncomeFrequency;
  occurrences: number;
  pattern: string;
  last_date: string;
  confidence: number;
  last_transaction_id: string | null;
}
```

---

## Suggested Page Layouts

### Option A: Add to Existing Dashboard

Integrate insights at the top of the dashboard:

```
┌─────────────────────────────────────────────────────────────┐
│ Today's Insights                                    [1/12]  │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│ │ 🚨 Alert    │ │ 🎉 Opport.  │ │ 🎯 Optimize │            │
│ │             │ │             │ │             │            │
│ │ Spending    │ │ You saved   │ │ Plan your   │            │
│ │ is high...  │ │ $1116...    │ │ meals...    │            │
│ │             │ │             │ │             │            │
│ │ [Helpful]   │ │ [Helpful]   │ │ [Helpful]   │            │
│ └─────────────┘ └─────────────┘ └─────────────┘            │
├─────────────────────────────────────────────────────────────┤
│ [Existing dashboard widgets...]                             │
└─────────────────────────────────────────────────────────────┘
```

### Option B: Separate Insights Page

```
/insights
┌─────────────────────────────────────────────────────────────┐
│ Your Financial Insights                        Jan 12, 2026 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [Today's Insights - 3 cards]                                │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Insight History                                             │
│                                                             │
│ • Jan 11 - "You're on track!" [Acted on]                   │
│ • Jan 10 - "Consider reducing..." [Helpful]                │
│ • ...                                                       │
└─────────────────────────────────────────────────────────────┘
```

### Goals Page

```
/goals
┌─────────────────────────────────────────────────────────────┐
│ Financial Goals                              [+ New Goal]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Active Goals                                                │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 🎯 Honeymoon Fund                               [Edit]  ││
│ │ $1,000 / $6,000 (16.7%)  ████░░░░░░░░░░░░░░░  On Track ││
│ │ Due: May 1, 2026 | Monthly: $1,250                      ││
│ │ [+ Add Progress]                                        ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ Suggested Goals                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 💡 Emergency Fund - Save $16,000                        ││
│ │ "Financial experts recommend 3-6 months..."             ││
│ │ [Accept]                                                ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Priority

### Phase 1 (Core)
1. `InsightsPanel` + `InsightCard` - Display daily insights
2. `GoalsList` + `GoalCard` - Display goals
3. API hooks and functions

### Phase 2 (CRUD)
4. `GoalForm` - Create/edit goals
5. Feedback buttons on insights
6. Goal progress updates

### Phase 3 (Settings)
7. `ProfileSettings` - Context for LLM
8. `IncomeManager` - Income sources
9. `GoalSuggestions` - Auto-suggested goals

---

## Existing Components to Reuse

Your frontend already has these that can be adapted:

| Existing Component | Can Use For |
|-------------------|-------------|
| `InsightCard` (dashboard) | Base for new `InsightCard` |
| `SpendingVelocity` | Reference for progress bars |
| `CategoryBreakdownWidget` | Reference for card styling |
| UI components in `src/components/ui/` | Buttons, modals, inputs |

---

## Quick Start

1. Create the types file with all TypeScript interfaces
2. Add the API functions to `src/lib/api.ts`
3. Add the hooks to `src/lib/hooks.ts`
4. Build `InsightCard` component
5. Build `InsightsPanel` that uses the hook
6. Add to dashboard or create new page

The backend is ready and tested. Just call the endpoints!
