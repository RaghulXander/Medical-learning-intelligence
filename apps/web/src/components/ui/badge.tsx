import * as React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?:
    | 'default'
    | 'secondary'
    | 'destructive'
    | 'outline'
    | 'success'
    | 'warning'
    | 'verified'
    | 'suggested';
}

function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const variants = {
    default:
      'border-transparent bg-sky-500/20 text-sky-300 border border-sky-500/30',
    secondary:
      'border-transparent bg-slate-800 text-slate-300 border border-white/[0.08]',
    destructive:
      'border-transparent bg-red-500/15 text-red-300 border border-red-500/30',
    outline: 'text-slate-300 border border-white/10 bg-white/[0.02]',
    success:
      'border-emerald-500/30 bg-emerald-500/15 text-emerald-300 border font-medium',
    warning:
      'border-amber-500/30 bg-amber-500/15 text-amber-300 border font-medium',
    verified:
      'border-sky-500/40 bg-sky-500/15 text-sky-300 border font-medium shadow-sm',
    suggested:
      'border-purple-500/40 bg-purple-500/15 text-purple-300 border border-dashed font-medium',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
