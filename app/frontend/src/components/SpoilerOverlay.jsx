export function SpoilerOverlay({ onReveal }) {
  return (
    <div className="relative mb-2">
      {/* ぼかし表示のダミーテキスト */}
      <p
        className="text-sm text-gray-600 select-none"
        style={{ filter: 'blur(8px)', userSelect: 'none' }}
      >
        スコアや試合結果の情報がここに表示されます。
      </p>
      {/* 解除ボタン */}
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
