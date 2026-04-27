'use client';

import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tag } from '@/lib/api';

interface TagBadgeProps {
  tag: Tag;
  onRemove?: () => void;
  size?: 'sm' | 'md';
  className?: string;
}

export function TagBadge({ tag, onRemove, size = 'sm', className }: TagBadgeProps) {
  // Use tag color or default to gray
  const bgColor = tag.color ? `${tag.color}20` : '#E5E7EB';
  const textColor = tag.color || '#374151';
  const borderColor = tag.color ? `${tag.color}40` : '#D1D5DB';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-medium border',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
        className
      )}
      style={{
        backgroundColor: bgColor,
        color: textColor,
        borderColor: borderColor,
      }}
    >
      {tag.name}
      {onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="hover:opacity-70 transition-opacity"
        >
          <X className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
        </button>
      )}
    </span>
  );
}
