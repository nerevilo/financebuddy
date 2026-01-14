'use client';

import Link from 'next/link';
import { AlertTriangle, ArrowRight } from 'lucide-react';

interface UnusualTransactionsBadgeProps {
  count: number;
}

export function UnusualTransactionsBadge({ count }: UnusualTransactionsBadgeProps) {
  if (count === 0) return null;

  return (
    <Link
      href="/transactions?unusual=true"
      className="flex items-center gap-3 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl hover:bg-amber-100 hover:border-amber-300 transition-colors group"
    >
      <div className="flex items-center justify-center w-10 h-10 bg-amber-100 rounded-lg group-hover:bg-amber-200 transition-colors">
        <AlertTriangle className="w-5 h-5 text-amber-600" />
      </div>
      <div className="flex-1">
        <span className="font-medium text-amber-800">
          {count} unreviewed unusual transaction{count !== 1 ? 's' : ''}
        </span>
        <p className="text-sm text-amber-600">Click to review and categorize</p>
      </div>
      <ArrowRight className="w-5 h-5 text-amber-400 group-hover:text-amber-600 group-hover:translate-x-0.5 transition" />
    </Link>
  );
}
