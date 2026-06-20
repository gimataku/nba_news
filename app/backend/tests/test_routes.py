"""T-12: 設定変更の即時反映 / T-13: パフォーマンス"""
import time
from datetime import datetime, timezone

from db.models import Article


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _insert_articles(session, count: int, is_spurs: int = 0):
    for i in range(count):
        prefix = "spurs" if is_spurs else "other"
        session.add(Article(
            link=f"https://example.com/{prefix}/{i}",
            title_original=f"Article {prefix} {i}",
            title_ja=f"記事 {prefix} {i}",
            source="hoops_rumors",
            is_spurs=is_spurs,
            fetched_at=_now_str(),
        ))


# ── T-12 ──────────────────────────────────────────────────────────────────────

def test_t12_spurs_filter_reflects_immediately(api_client, patch_db_session):
    """T-12 ケース1: spurs_filter_enabled=true 後、spurs_only=true でSpurs記事のみ返ること"""
    _, TestSessionLocal = patch_db_session

    with TestSessionLocal() as session:
        _insert_articles(session, 3, is_spurs=1)
        _insert_articles(session, 2, is_spurs=0)
        session.commit()

    resp = api_client.put("/api/settings", json={"spurs_filter_enabled": True})
    assert resp.status_code == 200

    resp = api_client.get("/api/settings")
    assert resp.status_code == 200
    assert resp.json()["spurs_filter_enabled"] is True

    resp = api_client.get("/api/news", params={"spurs_only": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert all(a["is_spurs"] is True for a in data["articles"])


def test_t12_spoiler_guard_reflects_immediately(api_client):
    """T-12 ケース2: spoiler_guard_enabled 変更後、GET /api/settings で即座に反映されること"""
    resp = api_client.put("/api/settings", json={"spoiler_guard_enabled": False})
    assert resp.status_code == 200

    resp = api_client.get("/api/settings")
    assert resp.status_code == 200
    assert resp.json()["spoiler_guard_enabled"] is False

    resp = api_client.put("/api/settings", json={"spoiler_guard_enabled": True})
    assert resp.status_code == 200

    resp = api_client.get("/api/settings")
    assert resp.json()["spoiler_guard_enabled"] is True


# ── T-13 ──────────────────────────────────────────────────────────────────────

def test_t13_api_response_time(api_client, patch_db_session):
    """T-13: 50件データがある状態でのAPIレスポンスタイムが1秒以内であること"""
    _, TestSessionLocal = patch_db_session

    with TestSessionLocal() as session:
        for i in range(50):
            session.add(Article(
                link=f"https://example.com/perf/{i}",
                title_original=f"Performance Article {i}",
                source="hoops_rumors",
                fetched_at=_now_str(),
            ))
        session.commit()

    start = time.time()
    resp = api_client.get("/api/news")
    elapsed = time.time() - start

    assert resp.status_code == 200
    assert resp.json()["total"] == 50
    assert elapsed < 1.0, f"レスポンスタイム {elapsed:.3f}s が1秒を超えた"
