import { useState, useCallback, useEffect } from 'react';

export function useNews() {
  const [articles, setArticles] = useState([]);
  const [apiStatus, setApiStatus] = useState({
    api_limit_exceeded: false,
    is_fallback: false,
    last_fetched_at: null,
  });
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [spursOnly, setSpursOnly] = useState(false);
  const [spoilerGuard, setSpoilerGuard] = useState(true);
  const [revealedIds, setRevealedIds] = useState(new Set());
  const [loading, setLoading] = useState(false);

  const fetchArticles = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        category: selectedCategory,
        spurs_only: spursOnly,
        limit: 50,
      });
      const [articlesRes, statusRes] = await Promise.all([
        fetch(`/api/articles?${params}`),
        fetch('/api/status'),
      ]);
      const data = await articlesRes.json();
      const status = await statusRes.json();
      setArticles(data.articles);
      setApiStatus(status);
    } catch (err) {
      console.error('fetchArticles error:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, spursOnly]);

  const toggleSpoilerGuard = async () => {
    const next = !spoilerGuard;
    setSpoilerGuard(next);
    await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spoiler_guard_enabled: next }),
    });
  };

  const toggleSpursFilter = async () => {
    const next = !spursOnly;
    setSpursOnly(next);
    await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spurs_filter_enabled: next }),
    });
  };

  const revealScore = (id) => {
    setRevealedIds((prev) => new Set([...prev, id]));
  };

  useEffect(() => {
    fetchArticles();
  }, [fetchArticles]);

  return {
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
    fetchArticles,
  };
}
