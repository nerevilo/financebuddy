'use client';

interface TimePeriodSelectorProps {
  selected: 'day' | 'week' | 'month';
  onChange: (period: 'day' | 'week' | 'month') => void;
}

export function TimePeriodSelector({ selected, onChange }: TimePeriodSelectorProps) {
  const options: Array<{ value: 'day' | 'week' | 'month'; label: string }> = [
    { value: 'day', label: 'Today' },
    { value: 'week', label: 'This Week' },
    { value: 'month', label: 'This Month' },
  ];

  return (
    <div className="inline-flex rounded-lg border border-neutral-300 bg-white p-1">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
            selected === option.value
              ? 'bg-primary-500 text-white shadow-sm'
              : 'text-neutral-700 hover:text-neutral-900 hover:bg-cream-50'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
