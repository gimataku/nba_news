"""IT-01〜IT-04: 結合テスト（scheduler→DB→API の連携検証）"""
import scheduler
from config import INIT_USERNAME, INIT_USER_PASSWORD
from db import crud
from db.models import Article


def _init_user():
    from auth.users import init_user
    init_user(crud)


# ── IT-01: 認証フロー → 記事取得 ─────────────────────────────────────────────

def test_it_01_auth_flow_and_news(raw_api_client):
    """IT-01: JWT取得→/api/news 200 / トークンなし→401"""
    _init_user()

    # 正しい認証情報でログイン → access_token 取得
    resp = raw_api_client.post(
        "/api/auth/login",
        json={"username": INIT_USERNAME, "password": INIT_USER_PASSWORD},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    # 取得トークンで GET /api/news → 200・必須フィールドあり
    resp = raw_api_client.get(
        "/api/news",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "articles" in body
    assert "total" in body

    # トークンなし → 401（starlette 1.1.0 の実挙動）
    resp = raw_api_client.get("/api/news")
    assert resp.status_code == 401


# ── IT-02: Dedup Processor → DB保存 → APIフィルタリング ──────────────────────

def test_it_02_dedup_processor_db_api(mocker, api_client):
    """IT-02: 新規記事保存後、類似タイトル記事はis_duplicate=1で保存されAPIから除外されること"""
    article_a = {
        "link":    "https://example.com/it02-article-a",
        "title":   "Spurs Sign New Point Guard in Free Agency Deal",
        "summary": "San Antonio Spurs have signed a new point guard.",
    }

    mock_fetch = mocker.patch("scheduler.fetch_rss", return_value=(
        [article_a], "hoops_rumors", False,
    ))
    mocker.patch("scheduler.process_article", return_value={
        "title_ja":   "スパーズが新ポイントガードと契約",
        "summary_ja": "サンアントニオ・スパーズが新たなポイントガードと契約した。",
        "category":   "trade_fa",
        "has_score":  False,
    })

    # 1回目 run_batch: 記事Aを保存
    scheduler.run_batch()

    # 記事Aがis_duplicate=0でDBに存在することを確認
    articles = crud.get_articles(category="all")
    assert len(articles) == 1
    assert articles[0]["link"] == article_a["link"]

    # 記事B: 記事Aと類似タイトル（"Sign"→"Signs"、Levenshtein similarity ≈ 0.99 > 0.80）
    article_b = {
        "link":    "https://example.com/it02-article-b",
        "title":   "Spurs Signs New Point Guard in Free Agency Deal",
        "summary": "The Spurs have signed a point guard in free agency.",
    }
    mock_fetch.return_value = ([article_b], "hoops_rumors", False)

    # 2回目 run_batch: 記事Bは重複として処理される
    scheduler.run_batch()

    # GET /api/news で記事Bが除外されていることを確認
    resp = api_client.get("/api/news")
    assert resp.status_code == 200
    data = resp.json()
    links_in_response = [a["link"] for a in data["articles"]]
    assert article_b["link"] not in links_in_response

    # DB直接クエリで記事Bがis_duplicate=1で保存されていることを確認
    with crud.SessionLocal() as session:
        row = session.query(Article).filter_by(link=article_b["link"]).first()
    assert row is not None
    assert row.is_duplicate == 1


# ── IT-03: C-05バッチ → game_schedule UPSERT → GET /api/schedule ──────────

def test_it_03_game_schedule_batch_upsert_api(mocker, api_client):
    """IT-03: Scheduledで保存後、Finalにアップサートされた結果がDB・APIの両方に反映されること"""
    game_id   = "99001"
    game_date = "2026-06-28"

    # Scheduled 状態で1件 UPSERT
    mock_schedule = mocker.patch("scheduler.fetch_game_schedule", return_value=[{
        "id":                 int(game_id),
        "date":               f"{game_date}T00:00:00.000Z",
        "status":             "Scheduled",
        "home_team":          {"abbreviation": "SAS", "id": 27},
        "visitor_team":       {"abbreviation": "LAL", "id": 14},
        "home_team_score":    0,
        "visitor_team_score": 0,
    }])

    scheduler.run_game_schedule_batch()

    # DB確認: Scheduled・has_score=False
    games = crud.get_game_schedule(game_date, game_date)
    assert len(games) == 1
    assert games[0]["game_id"] == game_id
    assert games[0]["status"] == "Scheduled"
    assert games[0]["has_score"] is False

    # API確認
    resp = api_client.get("/api/schedule", params={"start_date": game_date, "end_date": game_date})
    assert resp.status_code == 200
    api_games = resp.json()["games"]
    assert len(api_games) == 1
    assert api_games[0]["status"] == "Scheduled"
    assert api_games[0]["has_score"] is False

    # 同一 game_id を Final・スコア付きで UPSERT
    mock_schedule.return_value = [{
        "id":                 int(game_id),
        "date":               f"{game_date}T00:00:00.000Z",
        "status":             "Final",
        "home_team":          {"abbreviation": "SAS", "id": 27},
        "visitor_team":       {"abbreviation": "LAL", "id": 14},
        "home_team_score":    112,
        "visitor_team_score": 105,
    }]

    scheduler.run_game_schedule_batch()

    # DB確認: Final・has_score=True・スコアあり
    games = crud.get_game_schedule(game_date, game_date)
    assert len(games) == 1
    assert games[0]["status"] == "Final"
    assert games[0]["has_score"] is True
    assert games[0]["home_score"] == 112
    assert games[0]["visitor_score"] == 105

    # API再取得で UPSERT 反映を確認
    resp = api_client.get("/api/schedule", params={"start_date": game_date, "end_date": game_date})
    assert resp.status_code == 200
    api_games = resp.json()["games"]
    assert len(api_games) == 1
    assert api_games[0]["status"] == "Final"
    assert api_games[0]["has_score"] is True
    assert api_games[0]["home_score"] == 112


# ── IT-04: Claude API分類 → カテゴリ別記事取得 ────────────────────────────────

def test_it_04_category_classification_and_filter(mocker, api_client):
    """IT-04: 4カテゴリ記事がバッチ処理後、カテゴリ別フィルタリングで正しく分類されること"""
    # タイトルは互いに類似度が低い（dedup が誤作動しないよう意図的に異なる文体）
    entries = [
        {
            "link":    "https://example.com/it04-trade",
            "title":   "Lakers Trade Anthony Davis to Memphis Grizzlies for Multiple Picks",
            "summary": "Breaking trade news from the Western Conference.",
        },
        {
            "link":    "https://example.com/it04-draft",
            "title":   "Wembanyama Wins NBA Draft Lottery Selection for Spurs",
            "summary": "The NBA Draft lottery results are in.",
        },
        {
            "link":    "https://example.com/it04-injury",
            "title":   "Stephen Curry Suffers Ankle Injury Doubtful for Playoff Run",
            "summary": "Golden State Warriors star is day-to-day.",
        },
        {
            "link":    "https://example.com/it04-column",
            "title":   "Eastern Conference Finals Preview Competitive Balance Column",
            "summary": "Analysis of the upcoming conference finals.",
        },
    ]
    categories = ["trade_fa", "draft", "injury", "column"]

    mocker.patch("scheduler.fetch_rss", return_value=(entries, "hoops_rumors", False))
    mocker.patch("scheduler.process_article", side_effect=[
        {"title_ja": f"記事{i}タイトル", "summary_ja": f"記事{i}の要約", "category": cat, "has_score": False}
        for i, cat in enumerate(categories)
    ])

    scheduler.run_batch()

    # trade_fa のみ → 1件
    resp = api_client.get("/api/news", params={"category": "trade_fa"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["articles"][0]["category"] == "trade_fa"

    # all → 4件全て
    resp = api_client.get("/api/news", params={"category": "all"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 4

    # game → 0件（gameカテゴリはフェーズ2で廃止済み）
    resp = api_client.get("/api/news", params={"category": "game"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
