// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m1-visual-cleanup.md
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-none font-mono font-medium transition-colors active:translate-y-[1px] active:brightness-95 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--color-bg-1)] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default: 'bg-[var(--color-accent)] text-[var(--color-bg-1)] hover:bg-[var(--color-accent)]/90',
        secondary:
          'bg-[var(--color-bg-2)] text-[var(--color-text)] border border-[var(--color-border)] hover:text-[var(--color-accent)]',
        outline:
          'border-[var(--color-border-strong)] bg-transparent text-[var(--color-text)] hover:text-[var(--color-accent)] hover:border-[var(--color-accent)]',
        ghost:
          'text-[var(--color-text-muted)] hover:text-[var(--color-accent)] hover:bg-[var(--color-accent)]/5',
        destructive:
          'bg-[var(--color-red)] text-[var(--color-bg-1)] hover:bg-[var(--color-red)]/90',
      },
      size: {
        default: 'h-8 px-3 py-1.5 text-xs tracking-[0.08em]',
        sm: 'h-7 px-2.5 py-1 text-xs tracking-[0.08em]',
        lg: 'h-9 px-4 py-2 text-sm tracking-[0.06em]',
        icon: 'h-8 w-8',
      },
    },
    compoundVariants: [
      { variant: 'default', size: 'icon', className: 'h-8 w-8' },
      { variant: 'secondary', size: 'icon', className: 'h-8 w-8' },
      { variant: 'outline', size: 'icon', className: 'h-8 w-8' },
      { variant: 'ghost', size: 'icon', className: 'h-8 w-8' },
      { variant: 'destructive', size: 'icon', className: 'h-8 w-8' },
    ],
    defaultVariants: {
      variant: 'default',
      size: 'default',
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
