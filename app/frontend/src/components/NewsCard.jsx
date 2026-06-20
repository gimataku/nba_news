import { SpoilerOverlay } from './SpoilerOverlay';

const BADGE_STYLES = {
  trade_fa: 'bg-orange-100 text-orange-700',
  draft:    'bg-green-100 text-green-700',
  injury:   'bg-red-100 text-red-700',
  column:   'bg-purple-100 text-purple-700',
};

const BADGE_LABELS = {
  trade_fa: 'トレード/FA',
  draft:    'ドラフト',
  injury:   'インジャリー',
  column:   'コラム',
};

function CategoryBadge({ category }) {
  if (!category) return null;
  return (
    <span
      className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${
        BADGE_STYLES[category] ?? 'bg-gray-100 text-gray-600'
      }`}
    >
      {BADGE_LABELS[category] ?? category}
    </span>
  );
}

function ScoreDisplay({ scoreData }) {
  let score;
  try {
    score = typeof scoreData === 'string' ? JSON.parse(scoreData) : scoreData;
  } catch {
    return null;
  }
  return (
    <span className="ml-2 font-mono text-xs text-gray-800">
      [{score.home_team} {score.home_score} - {score.visitor_score} {score.visitor_team}]
    </span>
  );
}

function formatRelativeTime(isoStr) {
  if (!isoStr) return '';
  const diff = Date.now() - new Date(isoStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}分前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}時間前`;
  const days = Math.floor(hours / 24);
  return `${days}日前`;
}

export function NewsCard({ article, spoilerGuard, isRevealed, onReveal, onHide }) {
  const needsSpoiler = spoilerGuard && article.has_score && !isRevealed;

  return (
    <div className="border rounded-lg p-4 mb-3 bg-white shadow-sm">
      <CategoryBadge category={article.category} />

      <h2 className="font-semibold text-sm mt-1 mb-2">
        {article.title_ja || article.title_original}
      </h2>

      {needsSpoiler ? (
        <SpoilerOverlay
          onReveal={() => onReveal(article.id)}
          onHide={() => onHide(article.id)}
          isRevealed={isRevealed}
          hasScore={article.has_score}
        />
      ) : (
        <>
          <p className="text-sm text-gray-600 mb-2">
            {article.summary_ja || '（翻訳データなし）'}
            {isRevealed && article.score_data && (
              <ScoreDisplay scoreData={article.score_data} />
            )}
          </p>
          {isRevealed && article.has_score && (
            <SpoilerOverlay
              onReveal={() => onReveal(article.id)}
              onHide={() => onHide(article.id)}
              isRevealed={isRevealed}
              hasScore={article.has_score}
            />
          )}
        </>
      )}

      <div className="text-xs text-gray-400">
        {article.source} · {formatRelativeTime(article.published_at)} ·{' '}
        <a
          href={article.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-500 underline"
        >
          原文を読む
        </a>
      </div>
    </div>
  );
}
