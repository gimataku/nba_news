import logging
from datetime import datetime, timedelta

import requests

from config import BALLDONTLIE_API_KEY, BALLDONTLIE_PER_PAGE, SPURS_TEAM_ID

logger = logging.getLogger(__name__)


def fetch_score(pub_date: datetime) -> dict | None:
    """
    pubDateから対象日を決定し、Spursの試合スコアを取得する。

    Returns:
        スコアデータ(dict) または None（試合なし・エラー）
    """
    # NBAの試合は現地時間の夜（UTC 18時以降）に開催されるため、
    # UTC 18時未満の記事は前日の試合を参照する
    if pub_date.hour < 18:
        target_date = (pub_date - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date = pub_date.strftime("%Y-%m-%d")

    url = "https://api.balldontlie.io/v1/games"
    params = {
        "team_ids[]": SPURS_TEAM_ID,
        "start_date": target_date,
        "end_date": target_date,
    }
    headers = {"Authorization": f"Bearer {BALLDONTLIE_API_KEY}"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        games = response.json().get("data", [])

        if not games:
            return None  # 試合なし → score_data=NULL

        game = games[0]
        return {
            "game_id":       game["id"],
            "home_team":     game["home_team"]["abbreviation"],
            "visitor_team":  game["visitor_team"]["abbreviation"],
            "home_score":    game["home_team_score"],
            "visitor_score": game["visitor_team_score"],
            "status":        game["status"],
            "period":        game.get("period", 0),
            "quarters":      [],  # 詳細クォータースコアは別エンドポイントのため省略
        }

    except (requests.RequestException, KeyError):
        logger.warning("BALLDONTLIE fetch error for date: %s", target_date)
        return None


def fetch_game_schedule(start_date: str, end_date: str) -> list[dict]:
    """
    C-05バッチ用：BALLDONTLIE /v1/games から全チームの試合日程を取得する。
    cursorページネーションで全ページを取得する（D-07対応）。
    Returns: 試合データのリスト（空リストの場合もあり）
    """
    url = "https://api.balldontlie.io/v1/games"
    headers = {"Authorization": f"Bearer {BALLDONTLIE_API_KEY}"}
    all_games = []
    cursor = None

    try:
        while True:
            params = {
                "start_date": start_date,
                "end_date": end_date,
                "per_page": BALLDONTLIE_PER_PAGE,
            }
            if cursor is not None:
                params["cursor"] = cursor

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            body = response.json()
            all_games.extend(body.get("data", []))

            cursor = body.get("meta", {}).get("next_cursor")
            if not cursor:
                break

        return all_games

    except (requests.RequestException, KeyError) as e:
        logger.warning("BALLDONTLIE game_schedule fetch error: %s", e)
        return all_games  # 取得済み分は返す（途中失敗でも部分データを活用）
