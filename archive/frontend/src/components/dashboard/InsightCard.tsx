'use client';

interface InsightCardProps {
  insight: {
    type: 'urgent' | 'important' | 'informational' | 'motivational';
    emoji: string;
    title: string;
    description: string;
    action: string;
    category: string | null;
  };
}

export function InsightCard({ insight }: InsightCardProps) {
  const getStyles = () => {
    switch (insight.type) {
      case 'urgent':
        return { border: 'border-secondary-300 bg-danger-50', icon: 'text-danger-500' };
      case 'important':
        return { border: 'border-orange-300 bg-warning-50', icon: 'text-warning-600' };
      case 'informational':
        return { border: 'border-primary-300 bg-primary-50', icon: 'text-primary-600' };
      case 'motivational':
        return { border: 'border-success-300 bg-success-50', icon: 'text-success-500' };
      default:
        return { border: 'border-neutral-300 bg-cream-50', icon: 'text-neutral-600' };
    }
  };

  const styles = getStyles();

  return (
    <div className={`rounded-xl border-2 ${styles.border} p-6 shadow-sm`}>
      <div className="flex items-start gap-4">
        <div className={`w-10 h-10 rounded-full bg-white flex items-center justify-center ${styles.icon}`}>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">
            Today's Insight
          </h3>
          <p className="text-lg font-semibold text-neutral-900 mb-2">
            {insight.title}
          </p>
          <p className="text-neutral-600 mb-3">
            {insight.description}
          </p>
          <p className="text-sm text-neutral-700 bg-white/50 rounded-lg px-3 py-2 inline-block">
            {insight.action}
          </p>
        </div>
      </div>
    </div>
  );
}
