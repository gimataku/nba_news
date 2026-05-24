import logging
from datetime import datetime, timedelta

import requests

from config import BALLDONTLIE_API_KEY, SPURS_TEAM_ID

logger = logging.getLogger(__name__)


def fetch_score(pub_date: datetime) -> dict | None:
    """
    pubDateから対象日を決定し、Spursの試合スコアを取得する。

    Returns:
        スコアデータ(dict) または None（試合なし・エラー）
    """
    if pub_date.hour < 12:
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
