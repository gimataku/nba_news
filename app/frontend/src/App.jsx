import { useNews } from './hooks/useNews';
import { CategoryTabs } from './components/CategoryTabs';
import { FilterBar } from './components/FilterBar';
import { NewsCard } from './components/NewsCard';

function ApiBanner({ apiStatus }) {
  if (!apiStatus.api_limit_exceeded && !apiStatus.is_fallback) return null;
  return (
    <div className="mb-3 space-y-1">
      {apiStatus.api_limit_exceeded && (
        <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 text-sm px-4 py-2 rounded">
          API上限に達しました。翻訳・要約は月次リセットまでスキップされます。
        </div>
      )}
      {apiStatus.is_fallback && (
        <div className="bg-red-50 border border-red-300 text-red-700 text-sm px-4 py-2 rounded">
          ニュース取得に失敗しました（フェールオーバー中）。
        </div>
      )}
    </div>
  );
}

export default function App() {
  const {
    articles,
    apiStatus,
    selectedCategory,
    spursOnly,
    spoilerGuard,
    revealedIds,
    loading,
    setSelectedCategory,
    toggleSpursFilter,
    toggleSpoilerGuard,
    revealScore,
  } = useNews();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-6">
        <h1 className="text-xl font-bold text-gray-900 mb-4">NBA ニュース</h1>

        <ApiBanner apiStatus={apiStatus} />

        <CategoryTabs
          selectedCategory={selectedCategory}
          onSelect={setSelectedCategory}
        />

        <FilterBar
          spursOnly={spursOnly}
          spoilerGuard={spoilerGuard}
          onToggleSpurs={toggleSpursFilter}
          onToggleSpoiler={toggleSpoilerGuard}
        />

        {loading ? (
          <p className="text-center text-gray-500 py-8">読み込み中...</p>
        ) : articles.length === 0 ? (
          <p className="text-center text-gray-500 py-8">記事がありません</p>
        ) : (
          articles.map((article) => (
            <NewsCard
              key={article.id}
              article={article}
              spoilerGuard={spoilerGuard}
              isRevealed={revealedIds.has(article.id)}
              onReveal={revealScore}
            />
          ))
        )}
      </div>
    </div>
  );
}
