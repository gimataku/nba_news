export function SpoilerOverlay({ onReveal, onHide, isRevealed, hasScore }) {
  if (isRevealed) {
    return hasScore ? (
      <button onClick={onHide} className="text-xs text-gray-400 underline mt-1">
        スコアを隠す
      </button>
    ) : null;
  }
  return (
    <div className="relative mb-2">
      <p
        className="text-sm text-gray-600 select-none"
        style={{ filter: 'blur(8px)', userSelect: 'none' }}
      >
        スコアや試合結果の情報がここに表示されます。
      </p>
      <div className="absolute inset-0 flex items-center justify-center">
        <button
          onClick={onReveal}
          className="bg-blue-600 text-white text-xs px-3 py-1 rounded-full hover:bg-blue-700 transition-colors"
        >
          スコアを表示
        </button>
      </div>
    </div>
  );
}
