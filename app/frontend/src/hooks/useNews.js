import { useState, useCallback, useEffect, useRef } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

const TAB_LIST = ['all', 'trade_fa', 'draft', 'schedule', 'injury', 'column'];
const API_CATEGORIES = ['all', 'trade_fa', 'draft', 'injury', 'column'];

export function useNews(token, onAuthError) {
  const onAuthErrorRef = useRef(onAuthError);
  onAuthErrorRef.current = onAuthError;

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
    if (selectedCategory === 'schedule') return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        category: selectedCategory,
        spurs_only: spursOnly,
        limit: 50,
      });
      const headers = { Authorization: `Bearer ${token}` };
      const [articlesRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/api/news?${params}`, { headers }),
        fetch(`${API_BASE}/api/status`, { headers }),
      ]);

      if (
        articlesRes.status === 401 || articlesRes.status === 403 ||
        statusRes.status === 401 || statusRes.status === 403
      ) {
        onAuthErrorRef.current();
        return;
      }

      const data = await articlesRes.json();
      const status = await statusRes.json();
      setArticles(data.articles);
      setApiStatus(status);
    } catch (err) {
      console.error('fetchArticles error:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, spursOnly, token]);

  const toggleSpoilerGuard = async () => {
    const next = !spoilerGuard;
    setSpoilerGuard(next);
    const res = await fetch(`${API_BASE}/api/settings`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ spoiler_guard_enabled: next }),
    });
    if (res.status === 401 || res.status === 403) onAuthErrorRef.current();
  };

  const toggleSpursFilter = async () => {
    const next = !spursOnly;
    setSpursOnly(next);
    const res = await fetch(`${API_BASE}/api/settings`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ spurs_filter_enabled: next }),
    });
    if (res.status === 401 || res.status === 403) onAuthErrorRef.current();
  };

  const revealScore = (id) => {
    setRevealedIds((prev) => new Set([...prev, id]));
  };

  const resetSpoiler = (id) => {
    setRevealedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
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
    resetSpoiler,
    fetchArticles,
  };
}
