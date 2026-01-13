import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full font-medium transition-colors',
  {
    variants: {
      variant: {
        primary: 'bg-primary-100 text-primary-800 border border-primary-200',
        secondary: 'bg-secondary-100 text-secondary-800 border border-secondary-200',
        success: 'bg-success-100 text-success-800 border border-success-200',
        danger: 'bg-danger-100 text-danger-800 border border-danger-200',
        warning: 'bg-warning-100 text-warning-800 border border-warning-200',
        neutral: 'bg-neutral-100 text-neutral-800 border border-neutral-200',
        outline: 'bg-transparent text-neutral-700 border border-neutral-300',
      },
      size: {
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-2.5 py-1 text-sm',
        lg: 'px-3 py-1.5 text-base',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
