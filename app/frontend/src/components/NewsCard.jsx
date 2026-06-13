import { SpoilerOverlay } from './SpoilerOverlay';

const BADGE_STYLES = {
  trade:    'bg-orange-100 text-orange-700',
  contract: 'bg-green-100 text-green-700',
  game:     'bg-blue-100 text-blue-700',
  column:   'bg-purple-100 text-purple-700',
};

const BADGE_LABELS = {
  trade:    'トレード',
  contract: '契約',
  game:     '試合結果',
  column:   'コラム',
};

function CategoryBadge({ category }) {
  if (!category) return null;
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${BADGE_STYLES[category] ?? 'bg-gray-100 text-gray-600'}`}>
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

export function NewsCard({ article, spoilerGuard, isRevealed, onReveal }) {
  const needsSpoiler =
    spoilerGuard &&
    (article.category === 'game' || article.has_score) &&
    !isRevealed;

  return (
    <div className="border rounded-lg p-4 mb-3 bg-white shadow-sm">
      <CategoryBadge category={article.category} />

      <h2 className="font-semibold text-sm mt-1 mb-2">
        {article.title_ja || article.title_original}
      </h2>

      {needsSpoiler ? (
        <SpoilerOverlay onReveal={() => onReveal(article.id)} />
      ) : (
        <p className="text-sm text-gray-600 mb-2">
          {article.summary_ja || '（翻訳データなし）'}
          {isRevealed && article.score_data && (
            <ScoreDisplay scoreData={article.score_data} />
          )}
        </p>
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
