"""T-08: スコア表示（BALLDONTLIEデータ取得）
T-P2-06: C-05バッチ（game_schedule UPSERT）"""
import json
from datetime import datetime, timezone

import responses as responses_lib

from fetcher.score import fetch_game_schedule, fetch_score

BALLDONTLIE_URL = "https://api.balldontlie.io/v1/games"

_GAME_DATA = {
    "data": [{
        "id": 999,
        "home_team": {"abbreviation": "SAS", "id": 27},
        "visitor_team": {"abbreviation": "LAL", "id": 14},
        "home_team_score": 110,
        "visitor_team_score": 105,
        "status": "Final",
        "period": 4,
    }]
}

_PUB_DATE_AFTERNOON = datetime(2026, 5, 14, 14, 0, 0, tzinfo=timezone.utc)
_PUB_DATE_MORNING   = datetime(2026, 5, 14,  9, 0, 0, tzinfo=timezone.utc)


@responses_lib.activate
def test_t08_game_found():
    """T-08 ケース1: 試合あり → スコアデータが返ること"""
    responses_lib.add(
        responses_lib.GET,
        BALLDONTLIE_URL,
        json=_GAME_DATA,
        status=200,
    )

    result = fetch_score(_PUB_DATE_AFTERNOON)

    assert result is not None
    assert isinstance(result["game_id"], int)
    assert isinstance(result["home_team"], str)
    assert isinstance(result["visitor_team"], str)
    assert isinstance(result["home_score"], int)
    assert isinstance(result["visitor_score"], int)
    assert result["status"] == "Final"


@responses_lib.activate
def test_t08_no_game():
    """T-08 ケース2: 試合なし → None が返ること"""
    responses_lib.add(
        responses_lib.GET,
        BALLDONTLIE_URL,
        json={"data": []},
        status=200,
    )

    result = fetch_score(_PUB_DATE_AFTERNOON)

    assert result is None


@responses_lib.activate
def test_t08_api_error():
    """T-08 ケース3: API失敗 → 例外を握りつぶして None が返ること"""
    responses_lib.add(
        responses_lib.GET,
        BALLDONTLIE_URL,
        status=500,
    )

    result = fetch_score(_PUB_DATE_AFTERNOON)

    assert result is None


# ── T-P2-06: game_schedule UPSERT ──────────────────────────────────────────────

def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _scheduled_game(game_id: str) -> dict:
    return {
        "game_id":      game_id,
        "game_date":    "2026-06-14",
        "status":       "Scheduled",
        "home_team":    "SAS",
        "visitor_team": "LAL",
        "home_score":   None,
        "visitor_score": None,
        "has_score":    0,
        "fetched_at":   _now_str(),
    }


def test_tc_p2_06_1_new_insert(patch_db_session):
    """TC-P2-06-1: game_id未登録・status=Scheduled → 新規INSERT / has_score=False"""
    _, TestSessionLocal = patch_db_session
    from db import crud
    from db.models import GameSchedule

    game = _scheduled_game("g001")
    crud.upsert_game_schedule(game)

    with TestSessionLocal() as session:
        row = session.query(GameSchedule).filter_by(game_id="g001").first()

    assert row is not None
    assert row.status == "Scheduled"
    assert row.has_score == 0
    assert row.home_score is None


def test_tc_p2_06_2_update_to_final(patch_db_session):
    """TC-P2-06-2: game_id既登録（Scheduled）→ status=Final で上書き / has_score=True"""
    _, TestSessionLocal = patch_db_session
    from db import crud
    from db.models import GameSchedule

    crud.upsert_game_schedule(_scheduled_game("g002"))

    final_game = {
        **_scheduled_game("g002"),
        "status":       "Final",
        "home_score":   110,
        "visitor_score": 105,
        "has_score":    1,
    }
    crud.upsert_game_schedule(final_game)

    with TestSessionLocal() as session:
        row = session.query(GameSchedule).filter_by(game_id="g002").first()

    assert row.status == "Final"
    assert row.has_score == 1
    assert row.home_score == 110
    assert row.visitor_score == 105


def test_tc_p2_06_3_update_to_in_progress(patch_db_session):
    """TC-P2-06-3: game_id既登録（Scheduled）→ status=In Progress で上書き / has_score=True"""
    _, TestSessionLocal = patch_db_session
    from db import crud
    from db.models import GameSchedule

    crud.upsert_game_schedule(_scheduled_game("g003"))

    in_progress_game = {
        **_scheduled_game("g003"),
        "status":       "In Progress",
        "home_score":   54,
        "visitor_score": 51,
        "has_score":    1,
    }
    crud.upsert_game_schedule(in_progress_game)

    with TestSessionLocal() as session:
        row = session.query(GameSchedule).filter_by(game_id="g003").first()

    assert row.status == "In Progress"
    assert row.has_score == 1


@responses_lib.activate
def test_tc_p2_06_4_api_500_returns_empty():
    """TC-P2-06-4: BALLDONTLIE API 500 → [] を返し例外なし（処理継続）"""
    responses_lib.add(responses_lib.GET, BALLDONTLIE_URL, status=500)

    result = fetch_game_schedule("2026-06-14", "2026-06-21")

    assert result == []


@responses_lib.activate
def test_fetch_game_schedule_success():
    """fetch_game_schedule: 正常レスポンス → 試合リストを返す"""
    game_data = {
        "data": [
            {
                "id": 1001,
                "date": "2026-06-14T00:00:00.000Z",
                "status": "Scheduled",
                "home_team": {"abbreviation": "SAS", "id": 27},
                "visitor_team": {"abbreviation": "LAL", "id": 14},
                "home_team_score": 0,
                "visitor_team_score": 0,
            }
        ],
        "meta": {"next_cursor": None},
    }
    responses_lib.add(
        responses_lib.GET, BALLDONTLIE_URL, json=game_data, status=200,
    )

    result = fetch_game_schedule("2026-06-14", "2026-06-21")

    assert len(result) == 1
    assert result[0]["id"] == 1001


@responses_lib.activate
def test_fetch_game_schedule_pagination():
    """fetch_game_schedule: cursorページネーションで全ページ取得する"""
    page1 = {
        "data": [{"id": 1, "date": "2026-06-14T00:00:00.000Z", "status": "Scheduled",
                  "home_team": {"abbreviation": "SAS", "id": 27},
                  "visitor_team": {"abbreviation": "LAL", "id": 14},
                  "home_team_score": 0, "visitor_team_score": 0}],
        "meta": {"next_cursor": 42},
    }
    page2 = {
        "data": [{"id": 2, "date": "2026-06-15T00:00:00.000Z", "status": "Scheduled",
                  "home_team": {"abbreviation": "GSW", "id": 9},
                  "visitor_team": {"abbreviation": "BOS", "id": 2},
                  "home_team_score": 0, "visitor_team_score": 0}],
        "meta": {"next_cursor": None},
    }
    responses_lib.add(responses_lib.GET, BALLDONTLIE_URL, json=page1, status=200)
    responses_lib.add(responses_lib.GET, BALLDONTLIE_URL, json=page2, status=200)

    result = fetch_game_schedule("2026-06-14", "2026-06-21")

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["id"] == 2


def test_delete_old_game_schedule(patch_db_session):
    """delete_old_game_schedule: 古いレコードを削除すること"""
    from datetime import timedelta

    _, TestSessionLocal = patch_db_session
    from db import crud
    from db.models import GameSchedule

    old_fetched_at = (
        datetime.now(timezone.utc) - timedelta(days=35)
    ).strftime("%Y-%m-%dT%H:%M:%S")

    with TestSessionLocal() as session:
        session.add(GameSchedule(
            game_id="old_game",
            game_date="2026-05-01",
            status="Final",
            home_team="SAS",
            visitor_team="LAL",
            has_score=1,
            fetched_at=old_fetched_at,
        ))
        session.commit()

    deleted = crud.delete_old_game_schedule()

    assert deleted == 1
