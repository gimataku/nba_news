import logging
import time

import feedparser
import requests

from config import RSS_SOURCES

logger = logging.getLogger(__name__)


def fetch_rss_source(source: dict) -> list:
    """
    requests.get() でコンテンツを取得し feedparser.parse(response.content) へ渡す。
    feedparser.parse() に直接 URL を渡さないことでタイムアウト制御を有効にする。
    """
    response = requests.get(
        source["url"],
        headers={"User-Agent": "NBANewsJP/1.0"},
        timeout=source["timeout"],  # (接続5秒, 読み取り10秒)
    )
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    return feed.entries


def fetch_rss() -> tuple[list, str, bool]:
    """
    Hoops Rumors → Hoops Wire → The Cold Wire NBA の順でフェールオーバー。

    Returns:
        (entries, source_name, is_fallback)
        全ソース失敗時は ([], "", True)
    """
    for i, source in enumerate(RSS_SOURCES):
        for attempt in range(source["retry"]):
            try:
                entries = fetch_rss_source(source)
                if entries:
                    return list(entries), source["name"], (i > 0)
                logger.warning(
                    "[%s] attempt %d: feed returned 0 entries",
                    source["name"], attempt + 1,
                )
            except Exception as exc:
                logger.warning(
                    "[%s] attempt %d failed: %s",
                    source["name"], attempt + 1, exc,
                )
            time.sleep(1)

    logger.error("All RSS sources failed")
    return [], "", True
