'use client';

import { cn } from '@/lib/utils';
import { AlertTriangle } from 'lucide-react';

interface UnusualBadgeProps {
  anomalyReason: string | null;
  size?: 'sm' | 'md';
  showLabel?: boolean;
  className?: string;
}

const REASON_LABELS: Record<string, string> = {
  z_score: 'Unusual amount',
  iqr_outlier: 'Outlier',
  category_spike: 'Category spike',
  new_large_merchant: 'New merchant',
};

export function UnusualBadge({
  anomalyReason,
  size = 'sm',
  showLabel = true,
  className,
}: UnusualBadgeProps) {
  const label = anomalyReason ? REASON_LABELS[anomalyReason] || 'Unusual' : 'Unusual';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full bg-warning-100 text-warning-700 border border-warning-200',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
        className
      )}
    >
      <AlertTriangle className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      {showLabel && <span className="font-medium">{label}</span>}
    </span>
  );
}
