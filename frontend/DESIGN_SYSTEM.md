# FinanceBuddy Design System

A professional, consistent design system for FinanceBuddy. This guide is optimized for both human developers and AI agents.

## Color Palette

### Primary Colors

**Primary (Slate Blue)** - Trust, stability, professionalism
```tsx
bg-primary-50    // Lightest
bg-primary-100
bg-primary-200
bg-primary-300
bg-primary-400
bg-primary-500
bg-primary-600   // Default
bg-primary-700
bg-primary-800
bg-primary-900
bg-primary-950   // Darkest
```

**Secondary (Teal)** - Growth, balance, secondary actions
```tsx
bg-secondary-50 to bg-secondary-950
```

**Success (Emerald)** - Positive values, gains, confirmations
```tsx
bg-success-50 to bg-success-950
```

**Danger (Red)** - Warnings, negative values, destructive actions
```tsx
bg-danger-50 to bg-danger-950
```

**Warning (Amber)** - Cautions, alerts, important notices
```tsx
bg-warning-50 to bg-warning-950
```

**Neutral (Gray)** - Backgrounds, borders, subtle elements
```tsx
bg-neutral-50 to bg-neutral-950
```

### Category Colors

For transaction categories, use the helper functions:

```tsx
import { getCategoryColor, getCategoryIcon } from '@/config/design-system';

const color = getCategoryColor('groceries'); // Returns hex color
const icon = getCategoryIcon('groceries');    // Returns lucide icon name
```

Available categories:
- groceries (emerald)
- dining (amber)
- shopping (violet)
- entertainment (pink)
- transportation (blue)
- utilities (gray)
- healthcare (red)
- travel (cyan)
- income (green)
- transfer (slate)
- uncategorized (light gray)

## Components

### Button

Professional button component with multiple variants.

```tsx
import { Button } from '@/components/ui';

// Variants
<Button variant="primary">Primary Action</Button>
<Button variant="secondary">Secondary Action</Button>
<Button variant="success">Success Action</Button>
<Button variant="danger">Delete</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="link">Link</Button>

// Sizes
<Button size="sm">Small</Button>
<Button size="md">Medium (default)</Button>
<Button size="lg">Large</Button>
<Button size="xl">Extra Large</Button>
<Button size="icon">Icon Only</Button>

// With Lucide Icons
import { ArrowRight, Trash2 } from 'lucide-react';

<Button>
  Continue
  <ArrowRight className="h-4 w-4" />
</Button>

<Button variant="danger" size="icon">
  <Trash2 className="h-4 w-4" />
</Button>
```

### Badge

Status indicators and labels.

```tsx
import { Badge } from '@/components/ui';

// Variants
<Badge variant="primary">Primary</Badge>
<Badge variant="secondary">Secondary</Badge>
<Badge variant="success">Success</Badge>
<Badge variant="danger">Danger</Badge>
<Badge variant="warning">Warning</Badge>
<Badge variant="neutral">Neutral</Badge>
<Badge variant="outline">Outline</Badge>

// Sizes
<Badge size="sm">Small</Badge>
<Badge size="md">Medium (default)</Badge>
<Badge size="lg">Large</Badge>

// With Icons
import { CheckCircle2 } from 'lucide-react';

<Badge variant="success">
  <CheckCircle2 className="h-3 w-3" />
  Verified
</Badge>
```

### Card

Flexible card container with composable sub-components.

```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui';
import { TrendingUp } from 'lucide-react';

<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Optional description text</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Card content goes here</p>
  </CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>

// Simple card
<Card className="p-6">
  <div className="flex items-center gap-2">
    <TrendingUp className="h-5 w-5 text-success" />
    <h3>Simple Card</h3>
  </div>
</Card>
```

## Icons

Use Lucide React for all icons. No emojis.

```tsx
import {
  ArrowRight,
  TrendingUp,
  TrendingDown,
  DollarSign,
  CreditCard,
  Wallet,
  ChevronRight,
  X,
  Check,
  AlertCircle,
  Info,
} from 'lucide-react';

// Standard sizes
<Icon className="h-4 w-4" />  // Small
<Icon className="h-5 w-5" />  // Medium
<Icon className="h-6 w-6" />  // Large

// With colors
<TrendingUp className="h-5 w-5 text-success" />
<TrendingDown className="h-5 w-5 text-danger" />
<AlertCircle className="h-5 w-5 text-warning" />
```

## Typography

Use consistent text styles across the application.

```tsx
// Headings
<h1 className="text-3xl font-bold text-neutral-900">Page Title</h1>
<h2 className="text-2xl font-semibold text-neutral-900">Section Title</h2>
<h3 className="text-lg font-semibold text-neutral-900">Card Title</h3>

// Body text
<p className="text-base text-neutral-700">Regular paragraph text</p>
<p className="text-sm text-neutral-600">Secondary text</p>
<p className="text-xs text-neutral-500">Caption or helper text</p>

// Emphasis
<span className="font-medium">Medium weight</span>
<span className="font-semibold">Semibold weight</span>
<span className="font-bold">Bold weight</span>
```

## Layout Patterns

### Container

```tsx
<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  {/* Content */}
</div>
```

### Grid

```tsx
// 2 column grid
<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
  <Card>...</Card>
  <Card>...</Card>
</div>

// 3 column grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <Card>...</Card>
  <Card>...</Card>
  <Card>...</Card>
</div>
```

### Flex

```tsx
// Horizontal layout
<div className="flex items-center justify-between gap-4">
  <span>Left</span>
  <span>Right</span>
</div>

// Vertical stack
<div className="flex flex-col gap-4">
  <div>Item 1</div>
  <div>Item 2</div>
</div>
```

## Spacing

Use consistent spacing throughout the application:

```tsx
gap-2    // 8px  - Tight spacing
gap-4    // 16px - Default spacing
gap-6    // 24px - Comfortable spacing
gap-8    // 32px - Section spacing

p-4      // 16px padding
p-6      // 24px padding
px-4     // Horizontal padding
py-2     // Vertical padding

mb-4     // 16px bottom margin
mt-6     // 24px top margin
```

## Borders & Shadows

```tsx
// Borders
border border-neutral-200           // Standard border
border-2 border-primary             // Emphasized border
divide-y divide-neutral-200         // Divider between items

// Border radius
rounded-lg                          // Standard (12px)
rounded-xl                          // Cards (16px)
rounded-full                        // Pills/avatars

// Shadows
shadow-sm                           // Subtle elevation
shadow-md                           // Standard elevation
shadow-lg                           // Emphasized elevation
```

## Best Practices

### DO

1. Use design system colors instead of arbitrary values
2. Use Lucide icons consistently
3. Use Button, Badge, and Card components
4. Follow the spacing scale
5. Use semantic color names (success, danger, warning)
6. Keep layouts responsive with Tailwind breakpoints

```tsx
// Good
<Button variant="danger">Delete Account</Button>
<Badge variant="success">Active</Badge>
<TrendingUp className="h-5 w-5 text-success" />

// Good - Responsive
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
```

### DON'T

1. Don't use emojis (use Lucide icons)
2. Don't use arbitrary color values
3. Don't use inline buttons without the Button component
4. Don't use inconsistent spacing

```tsx
// Bad - Don't do this
<button className="bg-blue-500 text-white px-4 py-2 rounded">
  Click me
</button>

// Bad - Don't use emojis
<span>📊 Dashboard</span>

// Bad - Arbitrary colors
<div className="bg-[#ff0000]">...</div>

// Good - Use design system
<Button variant="primary">Click me</Button>
<TrendingUp className="h-5 w-5" />
<div className="bg-danger">...</div>
```

## For AI Agents

When generating code for FinanceBuddy:

1. Always import components from `@/components/ui`
2. Use `getCategoryColor()` and `getCategoryIcon()` for categories
3. Import icons from `lucide-react`
4. Use semantic color variants: primary, secondary, success, danger, warning, neutral
5. Use consistent spacing: gap-4, p-6, mb-4, etc.
6. All cards should use the Card component
7. All buttons should use the Button component
8. Never use emojis - always use Lucide icons

Example:

```tsx
import { Button, Badge, Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { getCategoryColor, getCategoryIcon } from '@/config/design-system';
import { TrendingUp, ArrowRight } from 'lucide-react';

export function TransactionCard({ transaction }) {
  const categoryColor = getCategoryColor(transaction.category);
  const categoryIcon = getCategoryIcon(transaction.category);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon name={categoryIcon} className="h-5 w-5" />
          {transaction.merchant}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <Badge variant="neutral">{transaction.category}</Badge>
          <span className="text-lg font-semibold">{formatCurrency(transaction.amount)}</span>
        </div>
      </CardContent>
    </Card>
  );
}
```

## Configuration Files

- Design tokens: `frontend/src/config/design-system.ts`
- Tailwind config: `frontend/tailwind.config.js`
- Global styles: `frontend/src/app/globals.css`
- UI components: `frontend/src/components/ui/`

## Summary

This design system provides:
- Professional, finance-focused color palette
- Reusable UI components (Button, Badge, Card)
- Consistent spacing and typography
- Lucide icons (no emojis)
- Clear guidelines for human and AI developers

Always refer to this guide when building new features or modifying existing ones.
