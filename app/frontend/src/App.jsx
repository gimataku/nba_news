import { useAuth } from './hooks/useAuth';
import { useNews } from './hooks/useNews';
import { LoginForm } from './components/LoginForm';
import { GameSchedule } from './components/GameSchedule';
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
  const { token, isAuthenticated, login, logout } = useAuth();

  if (!isAuthenticated) {
    return <LoginForm onLogin={login} />;
  }

  return <MainView token={token} logout={logout} />;
}

function MainView({ token, logout }) {
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
    resetSpoiler,
  } = useNews(token, logout);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold text-gray-900">NBA ニュース</h1>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            ログアウト
          </button>
        </div>

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

        {selectedCategory === 'schedule' ? (
          <GameSchedule token={token} />
        ) : loading ? (
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
              onHide={resetSpoiler}
            />
          ))
        )}
      </div>
    </div>
  );
}
