"""T-12: 設定変更の即時反映 / T-13: パフォーマンス
T-P2-02: JWT認証ガード / T-P2-05: 重複記事フィルタリング / T-P2-07: 試合日程API"""
import time
from datetime import datetime, timezone

from db.models import Article, GameSchedule


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


# ── T-P2-02: JWT認証ガード ─────────────────────────────────────────────────────

def test_tc_p2_02_1_no_auth_header(raw_api_client):
    """TC-P2-02-1: Authorizationヘッダーなし → HTTP 401（FastAPI 0.136.3 / starlette 1.1.0の実挙動）"""
    resp = raw_api_client.get("/api/news")
    assert resp.status_code == 401


def test_tc_p2_02_2_tampered_token(raw_api_client):
    """TC-P2-02-2: 改ざんされたトークン → HTTP 401"""
    resp = raw_api_client.get(
        "/api/news",
        headers={"Authorization": "Bearer tampered.invalid.token"},
    )
    assert resp.status_code == 401


def test_tc_p2_02_3_expired_token(raw_api_client):
    """TC-P2-02-3: 期限切れトークン → HTTP 401"""
    from datetime import timedelta

    from jose import jwt as jose_jwt

    from config import JWT_ALGORITHM, SECRET_KEY

    expired_payload = {
        "sub": "testuser",
        "exp": datetime.utcnow() - timedelta(hours=1),
    }
    expired_token = jose_jwt.encode(expired_payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

    resp = raw_api_client.get(
        "/api/news",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401


def test_tc_p2_02_4_valid_token(raw_api_client):
    """TC-P2-02-4: 有効なトークン → HTTP 200"""
    from auth.jwt import create_access_token

    token = create_access_token({"sub": "testuser"})
    resp = raw_api_client.get(
        "/api/news",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


# ── T-P2-05: 重複記事フィルタリング ───────────────────────────────────────────

def _insert_article(session, link: str, is_duplicate: int = 0):
    session.add(Article(
        link=link,
        title_original=f"Article {link}",
        source="hoops_rumors",
        is_duplicate=is_duplicate,
        fetched_at=_now_str(),
    ))


def test_tc_p2_05_1_all_non_duplicate(api_client, patch_db_session):
    """TC-P2-05-1: is_duplicate=False の記事3件 → 3件全て返る"""
    _, TestSessionLocal = patch_db_session

    with TestSessionLocal() as session:
        for i in range(3):
            _insert_article(session, f"https://example.com/nd/{i}", is_duplicate=0)
        session.commit()

    resp = api_client.get("/api/news")
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


def test_tc_p2_05_2_mixed_duplicate(api_client, patch_db_session):
    """TC-P2-05-2: is_duplicate=True 1件・False 2件 → False の2件のみ返る"""
    _, TestSessionLocal = patch_db_session

    with TestSessionLocal() as session:
        _insert_article(session, "https://example.com/dup/0", is_duplicate=1)
        _insert_article(session, "https://example.com/non/0", is_duplicate=0)
        _insert_article(session, "https://example.com/non/1", is_duplicate=0)
        session.commit()

    resp = api_client.get("/api/news")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for article in data["articles"]:
        assert "dup" not in article["link"]


def test_tc_p2_05_3_all_duplicate(api_client, patch_db_session):
    """TC-P2-05-3: is_duplicate=True のみ3件 → 0件返る"""
    _, TestSessionLocal = patch_db_session

    with TestSessionLocal() as session:
        for i in range(3):
            _insert_article(session, f"https://example.com/dup/{i}", is_duplicate=1)
        session.commit()

    resp = api_client.get("/api/news")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── T-P2-07: 試合日程API ──────────────────────────────────────────────────────

def _insert_game(session, game_id: str, game_date: str):
    session.add(GameSchedule(
        game_id=game_id,
        game_date=game_date,
        status="Scheduled",
        home_team="SAS",
        visitor_team="LAL",
        has_score=0,
        fetched_at=_now_str(),
    ))


def test_tc_p2_07_1_schedule_with_data(api_client, patch_db_session):
    """TC-P2-07-1: 有効JWT + 期間内データあり → games リストが返る"""
    _, TestSessionLocal = patch_db_session

    with TestSessionLocal() as session:
        _insert_game(session, "g001", "2026-06-14")
        _insert_game(session, "g002", "2026-06-18")
        session.commit()

    resp = api_client.get(
        "/api/schedule",
        params={"start_date": "2026-06-14", "end_date": "2026-06-21"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "games" in data
    assert len(data["games"]) == 2


def test_tc_p2_07_2_schedule_no_data(api_client):
    """TC-P2-07-2: 対象期間にデータなし → games が空リスト"""
    resp = api_client.get(
        "/api/schedule",
        params={"start_date": "2026-06-14", "end_date": "2026-06-21"},
    )
    assert resp.status_code == 200
    assert resp.json()["games"] == []


def test_tc_p2_07_3_schedule_no_jwt(raw_api_client):
    """TC-P2-07-3: JWTなし → HTTP 401（FastAPI 0.136.3 / starlette 1.1.0の実挙動）"""
    resp = raw_api_client.get(
        "/api/schedule",
        params={"start_date": "2026-06-14", "end_date": "2026-06-21"},
    )
    assert resp.status_code == 401


# ── GET /api/status・POST /api/fetch ──────────────────────────────────────────

def test_get_status(api_client):
    """GET /api/status → HTTP 200 / 必須フィールドを返す"""
    resp = api_client.get("/api/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "last_fetched_at" in body
    assert "api_limit_exceeded" in body


def test_post_fetch(api_client, mocker):
    """POST /api/fetch → HTTP 200 / バックグラウンドタスクが登録される"""
    mocker.patch("api.routes.run_batch")
    resp = api_client.post("/api/fetch")
    assert resp.status_code == 200
