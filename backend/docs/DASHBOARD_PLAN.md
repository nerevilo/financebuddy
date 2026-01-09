# Finance Buddy Dashboard - Design Plan

## 📊 Dashboard Layout Mockup

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Finance Buddy                                    [Profile] [Settings]       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  Total      │  │  This Month │  │  Merchants  │  │  Internal   │      │
│  │  Spent      │  │  Spending   │  │  Tracked    │  │  Transfers  │      │
│  │  $12,450    │  │  $1,234     │  │  295        │  │  497        │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────┐   │
│  │  Spending by Category            │  │  Monthly Trend               │   │
│  │  ─────────────────────           │  │  ──────────────              │   │
│  │                                  │  │                              │   │
│  │     🛒 Groceries    $4,234      │  │      📈 Line chart           │   │
│  │     🍔 Dining       $2,145      │  │         showing spending     │   │
│  │     ⛽ Gas          $1,234      │  │         Jun-Jan              │   │
│  │     💻 Software     $891        │  │                              │   │
│  │     ✈️ Travel       $1,850      │  │                              │   │
│  │     🏫 Education    $2,096      │  │                              │   │
│  │                                  │  │                              │   │
│  │  [View Pie Chart]                │  │                              │   │
│  └──────────────────────────────────┘  └──────────────────────────────┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────┐   │
│  │  Top Merchants                   │  │  Recent Transactions         │   │
│  │  ─────────────                   │  │  ────────────────           │   │
│  │                                  │  │                              │   │
│  │  1. Kroger          $892 (21x)  │  │  🛒 Kroger                   │   │
│  │  2. Costco          $654 (17x)  │  │      $14.95 • Jan 8          │   │
│  │  3. University MI   $512 (5x)   │  │                              │   │
│  │  4. Relish ezCater  $445 (10x)  │  │  💻 Claude AI                │   │
│  │  5. Domino's        $398 (7x)   │  │      $20.00 • Jan 8          │   │
│  │                                  │  │                              │   │
│  │  [View All →]                    │  │  🍕 Domino's                 │   │
│  │                                  │  │      $11.12 • Jan 7          │   │
│  │                                  │  │                              │   │
│  │                                  │  │  [View All →]                │   │
│  └──────────────────────────────────┘  └──────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Components Breakdown

### 1. **Header Stats Cards** (Top Row)
- **Total Spent**: Sum of all transactions (excluding internal transfers)
- **This Month**: Current month spending
- **Merchants Tracked**: Count of unique enriched merchants (295)
- **Internal Transfers**: Count of skipped transactions (497)

### 2. **Spending by Category** (Left, Middle)
**Data shown:**
- List of categories sorted by total spend
- Each row: emoji + category name + total amount
- Top 6-8 categories displayed
- Optional: Toggle to pie chart view

**Categories from your data:**
- 🛒 Groceries (Kroger, Costco, Aldi, Publix, etc.)
- 🍔 Dining (Domino's, Five Guys, restaurants)
- ⛽ Gas Stations (Shell, BP, Speedway, etc.)
- 💻 Software (Claude AI, Cursor, Replit, OpenAI)
- ✈️ Travel (Delta, American, Hotels)
- 🏫 Education (University of Michigan, MSU)
- ☕ Coffee (Starbucks, Gong Cha, JavaBlu)
- 🏥 Healthcare
- 🛍️ Shopping (Amazon, Target)

### 3. **Monthly Trend** (Right, Middle)
**Data shown:**
- Line chart showing spending per month
- X-axis: Jun 2025 → Jan 2026
- Y-axis: Total spending ($)
- Hover to see exact amounts

### 4. **Top Merchants** (Left, Bottom)
**Data shown:**
- Top 5-10 merchants by total spend
- Format: `Rank. Merchant Name  $amount (Nx)`
- Click merchant → filter transactions

### 5. **Recent Transactions** (Right, Bottom)
**Data shown:**
- Last 5-10 transactions
- Format: emoji + merchant + amount + date
- Click → view transaction details

---

## 🎯 What's NOT Included (Yet)

These features could be added later:
- ❌ Budget tracking / limits
- ❌ Savings goals
- ❌ Bill reminders
- ❌ Custom categories
- ❌ Export to CSV
- ❌ Date range filters (beyond month)
- ❌ Search transactions
- ❌ Merchant logos
- ❌ Location map of spending

---

## 🛠️ Tech Stack Proposal

**Frontend:**
- **Framework**: Next.js (already in your project)
- **Charts**: Recharts or Chart.js (lightweight, good for React)
- **Styling**: Tailwind CSS (fast, modern)
- **Icons**: Lucide React (clean, customizable)

**Backend:**
- **API**: FastAPI (already built)
- **Endpoints needed**:
  - `GET /dashboard/stats` - Summary stats
  - `GET /dashboard/spending-by-category` - Category breakdown
  - `GET /dashboard/monthly-trend` - Time series data
  - `GET /dashboard/top-merchants` - Top merchants list
  - `GET /transactions/recent` - Recent transactions

---

## 📱 Responsive Design

- **Desktop**: 2-column layout (as shown above)
- **Tablet**: Stack sections vertically
- **Mobile**: Single column, cards expand to full width

---

## 🎨 Color Scheme Ideas

**Option 1: Clean & Professional**
- Primary: Blue (#3B82F6)
- Success: Green (#10B981)
- Warning: Yellow (#F59E0B)
- Danger: Red (#EF4444)
- Background: White/Light Gray

**Option 2: Dark Mode**
- Primary: Purple (#8B5CF6)
- Background: Dark Gray (#1F2937)
- Cards: Darker Gray (#111827)
- Text: White/Light Gray

---

## ❓ Questions for You

1. **Layout**: Do you like the 2-column layout? Or prefer single column?

2. **Stats Cards**: Are these 4 stats useful? Want different ones?

3. **Charts**:
   - Spending by Category: List or Pie Chart?
   - Monthly Trend: Line chart good?

4. **Top Merchants**: Show top 5 or top 10?

5. **Recent Transactions**: How many? 5, 10, 20?

6. **Colors**: Clean/Professional or Dark Mode?

7. **Priority Features**: Which section is MOST important?
   - Category breakdown?
   - Monthly trends?
   - Top merchants?
   - Recent transactions?

8. **Missing Features**: Anything you NEED that's not here?

---

## 🚀 Implementation Order (If Approved)

1. **Phase 1**: Backend API endpoints (1-2 hours)
2. **Phase 2**: Dashboard layout + stats cards (1 hour)
3. **Phase 3**: Category breakdown + charts (1-2 hours)
4. **Phase 4**: Top merchants + recent transactions (1 hour)
5. **Phase 5**: Polish + responsive design (1 hour)

**Total estimate**: 5-7 hours of work

---

## 💭 Alternative: Minimal MVP First?

If you want to move FASTER, we could start with:
- Just stats cards (4 numbers)
- Just category breakdown (list)
- Just recent transactions (table)

No charts, no fancy stuff. Get it working in 2-3 hours, then iterate.

What do you think?
