# LLM-Powered Daily Insights System

## Overview

This document describes the new financial insights system that provides personalized, AI-generated daily insights using Gemini Flash (FREE tier - 1,500 requests/day).

## What Was Built

### Database Models

Four new tables were added to support the insights system:

#### 1. `user_profiles`
Extended user context for LLM personalization.

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (UUID) | Primary key |
| `user_id` | String (FK) | Reference to users table |
| `monthly_income_estimate` | Float | Auto-calculated or manual |
| `household_size` | Integer | Default: 1 |
| `location_city` | String | e.g., "Ann Arbor" |
| `location_state` | String | e.g., "MI" |
| `context_notes` | Text | Free-form context for LLM (e.g., "Saving for honeymoon") |
| `insight_frequency` | String | "daily" or "weekly" |
| `preferred_categories` | JSON | Categories to focus on |

#### 2. `income_sources`
Detected or manually entered income sources.

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (UUID) | Primary key |
| `user_id` | String (FK) | Reference to users table |
| `name` | String | e.g., "Employer Paycheck" |
| `amount` | Float | Per-period amount |
| `frequency` | String | weekly, biweekly, monthly, yearly, irregular |
| `auto_detected` | Boolean | True if detected from transactions |
| `detection_pattern` | String | Pattern that matched |
| `next_expected_date` | Date | When next income is expected |
| `is_active` | Boolean | Whether to include in calculations |

#### 3. `goals`
Financial goals with progress tracking.

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (UUID) | Primary key |
| `user_id` | String (FK) | Reference to users table |
| `name` | String | e.g., "Honeymoon Fund" |
| `description` | Text | Optional description |
| `target_amount` | Float | Goal target |
| `current_amount` | Float | Current progress |
| `monthly_allocation` | Float | Auto-calculated if deadline set |
| `deadline` | Date | Target completion date |
| `priority` | String | high, medium, low |
| `status` | String | active, completed, paused, cancelled |
| `auto_suggested` | Boolean | True if system suggested |
| `suggestion_reason` | Text | Why it was suggested |

#### 4. `insights`
LLM-generated daily insights with user feedback.

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (UUID) | Primary key |
| `user_id` | String (FK) | Reference to users table |
| `type` | String | alert, opportunity, optimization |
| `title` | String | Attention-grabbing headline |
| `description` | Text | 2-3 sentence explanation |
| `action` | Text | Specific actionable step |
| `emoji` | String | Visual indicator |
| `category` | String | Related spending category |
| `amount_referenced` | Float | Dollar amount mentioned |
| `priority_score` | Float | 0.0-1.0 for ranking |
| `feedback` | String | helpful, acted_on, dismissed, none |
| `feedback_at` | DateTime | When feedback was given |
| `generated_at` | DateTime | When insight was created |
| `expires_at` | DateTime | 24 hours after generation |
| `is_read` | Boolean | Whether user has seen it |
| `llm_source` | String | gemini_flash, fallback |
| `generation_cost` | Float | API cost (0 for free tier) |

---

## API Endpoints

### Profile API (`/api/profile`)

```
GET  /api/profile/          → Get user profile (creates default if none)
PATCH /api/profile/         → Update profile fields
```

**Example Response:**
```json
{
  "id": "uuid",
  "user_id": "default-user",
  "household_size": 2,
  "location_city": "Ann Arbor",
  "location_state": "MI",
  "context_notes": "Saving for honeymoon. Husband is a student.",
  "insight_frequency": "daily",
  "monthly_income_estimate": 5446.7
}
```

### Income API (`/api/income`)

```
GET  /api/income/                  → Income summary with all sources
POST /api/income/                  → Create manual income source
POST /api/income/detect            → Auto-detect from transaction patterns
POST /api/income/detect/{idx}/save → Save a detected source
PATCH /api/income/{id}             → Update income source
DELETE /api/income/{id}            → Delete income source
```

**Example Summary Response:**
```json
{
  "total_monthly_income": 5446.7,
  "income_sources": [...],
  "auto_detected_count": 1,
  "manual_count": 1
}
```

### Goals API (`/api/goals`)

```
GET  /api/goals/                → List all goals
POST /api/goals/                → Create goal (auto-calculates monthly allocation)
GET  /api/goals/suggestions     → Get auto-suggested goals
GET  /api/goals/{id}            → Get specific goal with progress
PATCH /api/goals/{id}           → Update goal
POST /api/goals/{id}/progress   → Add progress amount
DELETE /api/goals/{id}          → Delete goal
```

**Example Goal Response:**
```json
{
  "id": "uuid",
  "name": "Honeymoon Fund",
  "target_amount": 6000.0,
  "current_amount": 1000.0,
  "monthly_allocation": 1250.0,
  "deadline": "2026-05-01",
  "priority": "high",
  "status": "active",
  "progress_percentage": 16.7,
  "months_to_goal": 4,
  "on_track": true
}
```

### Insights API (`/api/insights`)

```
GET  /api/insights/daily           → Get today's 3 insights (generates if needed)
GET  /api/insights/history         → Get historical insights with stats
POST /api/insights/{id}/feedback   → Submit feedback (helpful/acted_on/dismissed)
POST /api/insights/{id}/read       → Mark as read
POST /api/insights/regenerate      → Force regeneration (for testing)
```

**Example Daily Insights Response:**
```json
{
  "date": "2026-01-12",
  "insights": [
    {
      "id": "uuid",
      "type": "alert",
      "title": "Spending is trending high this month!",
      "description": "At your current pace, you're projected to spend $6152...",
      "action": "Review your spending from the past week.",
      "emoji": "🚨",
      "priority_score": 0.9,
      "feedback": "none",
      "is_read": false
    },
    {
      "type": "opportunity",
      "title": "Great job cutting back on rent!",
      "description": "Your rent decreased by 53%...",
      "action": "Transfer $1116 to your Honeymoon Fund today!",
      "emoji": "🎉",
      "priority_score": 0.6
    },
    {
      "type": "optimization",
      "title": "Offset gas increases with small cuts",
      "description": "Your gas spending increased by 61%...",
      "action": "Plan your meals for the week.",
      "emoji": "⛽",
      "priority_score": 0.4
    }
  ],
  "generation_source": "gemini_flash",
  "total_cost": 0.0
}
```

---

## How Insights Are Generated

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    InsightGenerationService                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Gather Context                                           │
│     ├── DashboardService.get_spending_velocity()            │
│     ├── DashboardService.get_monthly_comparison()           │
│     ├── GoalService.get_user_goals() + progress             │
│     ├── IncomeService.calculate_monthly_income()            │
│     └── UserProfile (context_notes, household_size, etc.)   │
│                                                              │
│  2. Build Prompt                                             │
│     └── Structured prompt with all financial context         │
│                                                              │
│  3. Call LLM (Gemini Flash)                                  │
│     └── Returns JSON array of 3 insights                     │
│                                                              │
│  4. Parse & Save                                             │
│     └── Store in insights table with metadata                │
│                                                              │
│  5. Fallback                                                 │
│     └── Rule-based insights if LLM fails                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Insight Types

| Type | Priority | Purpose | Example |
|------|----------|---------|---------|
| **alert** | 0.7-1.0 | Urgent issues needing attention | "Spending 50% higher than last month" |
| **opportunity** | 0.4-0.7 | Savings potential, wins | "You saved $200 on dining!" |
| **optimization** | 0.3-0.6 | Long-term improvements | "Consider meal planning" |

### LLM Context Includes

- Spending velocity (spent so far, daily average, projection)
- Category comparisons (this month vs last month)
- Active goals with progress percentages
- Monthly income and income/expense ratio
- User context notes (e.g., "saving for honeymoon")
- Household size and location

---

## Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `app/models/models.py` | Added UserProfile, IncomeSource, Goal, Insight models |
| `app/services/income_service.py` | Income detection and CRUD |
| `app/services/goal_service.py` | Goal management and suggestions |
| `app/services/insight_generation_service.py` | LLM integration and insight generation |
| `app/routers/profile.py` | Profile API endpoints |
| `app/routers/income.py` | Income API endpoints |
| `app/routers/goals.py` | Goals API endpoints |
| `app/routers/insights.py` | Insights API endpoints |
| `app/schemas/schemas.py` | Added Pydantic schemas for all new models |

### Modified Files

| File | Changes |
|------|---------|
| `app/models/__init__.py` | Export new models |
| `app/schemas/__init__.py` | Export new schemas |
| `app/routers/__init__.py` | Export new routers |
| `app/main.py` | Include new routers |

### Migration

```
alembic/versions/0295cc479611_add_insights_goals_income_profile_tables.py
```

---

## Environment Variables

The system uses these environment variables (already in your `.env`):

```env
GEMINI_API_KEY=your-gemini-api-key  # For LLM insights (FREE tier)
```

If `GEMINI_API_KEY` is not set, the system falls back to rule-based insights.
