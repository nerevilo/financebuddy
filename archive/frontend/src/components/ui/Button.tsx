import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary:
          'bg-primary text-white shadow-sm hover:bg-primary-700 focus-visible:ring-primary-600',
        secondary:
          'bg-secondary text-white shadow-sm hover:bg-secondary-700 focus-visible:ring-secondary-600',
        success:
          'bg-success text-white shadow-sm hover:bg-success-700 focus-visible:ring-success-600',
        danger:
          'bg-danger text-white shadow-sm hover:bg-danger-700 focus-visible:ring-danger-600',
        outline:
          'border-2 border-primary bg-transparent text-primary hover:bg-primary-50 focus-visible:ring-primary-600',
        ghost:
          'bg-transparent text-primary hover:bg-neutral-100 focus-visible:ring-primary-600',
        link: 'bg-transparent text-primary underline-offset-4 hover:underline focus-visible:ring-primary-600',
      },
      size: {
        sm: 'h-9 px-3 text-sm',
        md: 'h-10 px-4 text-base',
        lg: 'h-11 px-6 text-base',
        xl: 'h-12 px-8 text-lg',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
