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
  const getBorderColor = () => {
    switch (insight.type) {
      case 'urgent':
        return 'border-red-300 bg-red-50';
      case 'important':
        return 'border-orange-300 bg-orange-50';
      case 'informational':
        return 'border-blue-300 bg-blue-50';
      case 'motivational':
        return 'border-green-300 bg-green-50';
      default:
        return 'border-gray-300 bg-gray-50';
    }
  };

  return (
    <div className={`rounded-xl border-2 ${getBorderColor()} p-6 shadow-sm`}>
      <div className="flex items-start gap-4">
        <div className="text-4xl">{insight.emoji}</div>
        <div className="flex-1">
          <h3 className="text-lg font-bold text-gray-900 mb-1">
            💡 TODAY'S INSIGHT
          </h3>
          <p className="text-xl font-semibold text-gray-800 mb-2">
            {insight.title}
          </p>
          <p className="text-gray-600 mb-3">
            {insight.description}
          </p>
          <p className="text-sm text-gray-700 bg-white/50 rounded-lg px-3 py-2 inline-block">
            💡 {insight.action}
          </p>
        </div>
      </div>
    </div>
  );
}
