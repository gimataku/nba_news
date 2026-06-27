"""scheduler.py の判定ロジックテスト（check_and_run_batch / check_and_run_game_schedule_batch）"""
from datetime import datetime, timedelta, timezone

from db import crud


def _utc_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


# ── check_and_run_batch ────────────────────────────────────────────────────────

def test_check_and_run_batch_initial_run(mocker):
    """last_fetched_at="" (初回) → run_batch が呼ばれること"""
    mock_run = mocker.patch("scheduler.run_batch")
    crud.set_setting("last_fetched_at", "")

    import scheduler
    scheduler.check_and_run_batch()

    mock_run.assert_called_once()


def test_check_and_run_batch_too_soon(mocker):
    """前回取得から4時間未満 → run_batch が呼ばれないこと"""
    mock_run = mocker.patch("scheduler.run_batch")
    recent = datetime.now(timezone.utc) - timedelta(hours=2)
    crud.set_setting("last_fetched_at", _utc_str(recent))

    import scheduler
    scheduler.check_and_run_batch()

    mock_run.assert_not_called()


def test_check_and_run_batch_after_4hours(mocker):
    """前回取得から4時間以上経過 → run_batch が呼ばれること"""
    mock_run = mocker.patch("scheduler.run_batch")
    old = datetime.now(timezone.utc) - timedelta(hours=5)
    crud.set_setting("last_fetched_at", _utc_str(old))

    import scheduler
    scheduler.check_and_run_batch()

    mock_run.assert_called_once()


def test_check_and_run_batch_exactly_4hours(mocker):
    """前回取得からちょうど4時間（境界値） → run_batch が呼ばれること"""
    mock_run = mocker.patch("scheduler.run_batch")
    boundary = datetime.now(timezone.utc) - timedelta(hours=4, seconds=1)
    crud.set_setting("last_fetched_at", _utc_str(boundary))

    import scheduler
    scheduler.check_and_run_batch()

    mock_run.assert_called_once()


# ── check_and_run_game_schedule_batch ─────────────────────────────────────────

def test_check_and_run_game_schedule_batch_initial(mocker):
    """last_schedule_fetched_at="" (初回) → run_game_schedule_batch が呼ばれること"""
    mock_run = mocker.patch("scheduler.run_game_schedule_batch")
    crud.set_setting("last_schedule_fetched_at", "")

    import scheduler
    scheduler.check_and_run_game_schedule_batch()

    mock_run.assert_called_once()


def test_check_and_run_game_schedule_batch_too_soon(mocker):
    """前回取得から4時間未満 → run_game_schedule_batch が呼ばれないこと"""
    mock_run = mocker.patch("scheduler.run_game_schedule_batch")
    recent = datetime.now(timezone.utc) - timedelta(hours=1)
    crud.set_setting("last_schedule_fetched_at", _utc_str(recent))

    import scheduler
    scheduler.check_and_run_game_schedule_batch()

    mock_run.assert_not_called()


def test_check_and_run_game_schedule_batch_after_4hours(mocker):
    """前回取得から4時間以上経過 → run_game_schedule_batch が呼ばれること"""
    mock_run = mocker.patch("scheduler.run_game_schedule_batch")
    old = datetime.now(timezone.utc) - timedelta(hours=6)
    crud.set_setting("last_schedule_fetched_at", _utc_str(old))

    import scheduler
    scheduler.check_and_run_game_schedule_batch()

    mock_run.assert_called_once()


# ── _elapsed_hours ─────────────────────────────────────────────────────────────

def test_elapsed_hours_invalid_string():
    """不正な日時文字列 → float('inf') を返すこと"""
    from scheduler import _elapsed_hours

    result = _elapsed_hours("not-a-date")

    assert result == float("inf")


def test_elapsed_hours_recent():
    """1時間前の文字列 → 約1.0時間を返すこと"""
    from scheduler import _elapsed_hours

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    iso_str = _utc_str(one_hour_ago)

    elapsed = _elapsed_hours(iso_str)

    assert 0.9 <= elapsed <= 1.1


# ── run_batch: 月次リセット ────────────────────────────────────────────────────

def test_run_batch_monthly_reset(mocker):
    """月次リセット: api_limit_exceeded が "false" にリセットされること"""
    crud.set_setting("api_limit_exceeded", "true")
    crud.set_setting("api_reset_month", "2026-04")

    mocker.patch("scheduler.fetch_rss", return_value=([], "", True))

    import scheduler
    scheduler.run_batch()

    assert crud.get_setting("api_limit_exceeded") == "false"


# ── _parse_pub_date ────────────────────────────────────────────────────────────

def test_parse_pub_date_valid():
    """published_parsed が正しくセットされているentry → UTC datetimeを返すこと"""
    import time
    from scheduler import _parse_pub_date

    class MockEntry:
        published_parsed = time.gmtime(0)  # Unix epoch

    result = _parse_pub_date(MockEntry())

    assert result is not None
    assert result.year == 1970


def test_parse_pub_date_none():
    """published_parsed がNone → None を返すこと"""
    from scheduler import _parse_pub_date

    class MockEntry:
        published_parsed = None

    result = _parse_pub_date(MockEntry())

    assert result is None


def test_parse_pub_date_invalid():
    """published_parsed が不正な値 → except分岐で None を返すこと"""
    from scheduler import _parse_pub_date

    class MockEntry:
        published_parsed = "not-a-time-struct"

    result = _parse_pub_date(MockEntry())

    assert result is None


# ── run_batch: 記事処理ループ ──────────────────────────────────────────────────

def test_run_batch_processes_new_article(mocker):
    """run_batch: 新規記事がDBに保存されること（メインループの主要パスをカバー）"""
    mocker.patch("scheduler.fetch_rss", return_value=(
        [{
            "link":    "https://example.com/new_article_001",
            "title":   "Spurs Sign New Guard",
            "summary": "The Spurs signed a new player today.",
        }],
        "hoops_rumors",
        False,
    ))
    mocker.patch("scheduler.process_article", return_value=None)

    import scheduler
    scheduler.run_batch()

    assert crud.exists_article("https://example.com/new_article_001") is True
    assert crud.get_setting("last_fetched_at") != ""


def test_run_batch_skips_duplicate_url(mocker):
    """run_batch: URL重複記事はis_duplicateフラグを立てずスキップすること"""
    mocker.patch("scheduler.fetch_rss", return_value=(
        [{"link": "https://example.com/existing_url", "title": "Any Title", "summary": ""}],
        "hoops_rumors",
        False,
    ))
    mocker.patch("scheduler.crud.exists_article", return_value=True)

    import scheduler
    scheduler.run_batch()

    assert crud.get_setting("last_fetched_at") != ""


def test_run_batch_saves_levenshtein_duplicate(mocker):
    """run_batch: Levenshtein重複記事はis_duplicate=1で保存されること"""
    mocker.patch("scheduler.fetch_rss", return_value=(
        [{
            "link":    "https://example.com/similar_article",
            "title":   "Spurs Signs New Guard",
            "summary": "Spurs signed a player.",
        }],
        "hoops_rumors",
        False,
    ))
    mocker.patch("scheduler.is_duplicate", return_value=True)

    import scheduler
    scheduler.run_batch()

    from db.models import Article
    with crud.SessionLocal() as session:
        row = session.query(Article).filter_by(
            link="https://example.com/similar_article"
        ).first()
    assert row is not None
    assert row.is_duplicate == 1


# ── run_game_schedule_batch ──────────────────────────────────────────────────

def test_run_game_schedule_batch_success(mocker):
    """run_game_schedule_batch: 試合データを取得してUPSERTし、last_schedule_fetched_atを更新すること"""
    mock_games = [{
        "id":               9999,
        "date":             "2026-06-14T00:00:00.000Z",
        "status":           "Scheduled",
        "home_team":        {"abbreviation": "SAS", "id": 27},
        "visitor_team":     {"abbreviation": "LAL", "id": 14},
        "home_team_score":  0,
        "visitor_team_score": 0,
    }]
    mocker.patch("scheduler.fetch_game_schedule", return_value=mock_games)

    import scheduler
    scheduler.run_game_schedule_batch()

    assert crud.get_setting("last_schedule_fetched_at") != ""

    games = crud.get_game_schedule("2026-06-14", "2026-06-14")
    assert len(games) == 1
    assert games[0]["status"] == "Scheduled"
    assert games[0]["has_score"] is False


def test_run_game_schedule_batch_final_has_score(mocker):
    """run_game_schedule_batch: status=Final の試合はhas_score=Trueで保存されること"""
    mock_games = [{
        "id":               8888,
        "date":             "2026-06-13T00:00:00.000Z",
        "status":           "Final",
        "home_team":        {"abbreviation": "GSW", "id": 9},
        "visitor_team":     {"abbreviation": "BOS", "id": 2},
        "home_team_score":  115,
        "visitor_team_score": 108,
    }]
    mocker.patch("scheduler.fetch_game_schedule", return_value=mock_games)

    import scheduler
    scheduler.run_game_schedule_batch()

    games = crud.get_game_schedule("2026-06-13", "2026-06-13")
    assert len(games) == 1
    assert games[0]["has_score"] is True
    assert games[0]["home_score"] == 115


def test_run_game_schedule_batch_exception(mocker):
    """run_game_schedule_batch: 例外発生時もクラッシュせず継続すること"""
    mocker.patch(
        "scheduler.fetch_game_schedule",
        side_effect=RuntimeError("unexpected error"),
    )

    import scheduler
    scheduler.run_game_schedule_batch()  # 例外がここまで伝播しないこと
