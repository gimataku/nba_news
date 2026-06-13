export function FilterBar({ spursOnly, spoilerGuard, onToggleSpurs, onToggleSpoiler }) {
  return (
    <div className="flex items-center gap-3 py-2 px-1 mb-3 text-sm">
      {/* チームフィルタ */}
      <div className="flex rounded-md overflow-hidden border border-gray-300">
        <button
          onClick={onToggleSpurs}
          disabled={!spursOnly}
          className={
            'px-3 py-1 transition-colors ' +
            (!spursOnly ? 'bg-blue-500 text-white cursor-default' : 'bg-white text-gray-600 hover:bg-gray-50')
          }
        >
          全チーム
        </button>
        <button
          onClick={onToggleSpurs}
          disabled={spursOnly}
          className={
            'px-3 py-1 transition-colors ' +
            (spursOnly ? 'bg-blue-500 text-white cursor-default' : 'bg-white text-gray-600 hover:bg-gray-50')
          }
        >
          チームのみ
        </button>
      </div>

      {/* ネタバレ防止トグル */}
      <button
        onClick={onToggleSpoiler}
        className={
          'flex items-center gap-2 px-3 py-1 rounded-full border transition-colors ' +
          (spoilerGuard
            ? 'bg-blue-500 border-blue-500 text-white'
            : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50')
        }
      >
        <span
          className={
            'w-4 h-4 rounded-full border-2 transition-colors ' +
            (spoilerGuard ? 'bg-white border-white' : 'border-gray-400')
          }
        />
        ネタバレ防止 {spoilerGuard ? 'ON' : 'OFF'}
      </button>
    </div>
  );
}
