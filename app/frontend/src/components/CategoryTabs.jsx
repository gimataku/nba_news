const TABS = [
  { value: 'all',      label: 'すべて' },
  { value: 'trade',    label: 'トレード' },
  { value: 'contract', label: '契約' },
  { value: 'game',     label: '試合結果' },
  { value: 'column',   label: 'コラム' },
];

export function CategoryTabs({ selectedCategory, onSelect }) {
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-gray-200 mb-3">
      {TABS.map((tab) => {
        const isActive = tab.value === selectedCategory;
        return (
          <button
            key={tab.value}
            onClick={() => onSelect(tab.value)}
            className={
              'px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ' +
              (isActive
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300')
            }
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
