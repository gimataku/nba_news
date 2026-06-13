"""T-08: スコア表示（BALLDONTLIEデータ取得）"""
import json
from datetime import datetime, timezone

import responses as responses_lib

from fetcher.score import fetch_score

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
