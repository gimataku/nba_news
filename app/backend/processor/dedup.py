import logging

from Levenshtein import ratio

from config import DEDUP_THRESHOLD, DEDUP_WINDOW_DAYS

logger = logging.getLogger(__name__)


def is_duplicate(new_title: str, db) -> bool:
    """
    直近DEDUP_WINDOW_DAYS日のarticles.title_original（英語）と新規記事タイトルを比較し
    類似度がDEDUP_THRESHOLD以上の場合Trueを返す。
    翻訳前（英語タイトル）で比較することでコスト削減と整合性を確保する。
    """
    if not new_title:
        return False
    try:
        recent_titles = db.get_recent_titles(days=DEDUP_WINDOW_DAYS)
    except Exception:
        logger.warning("get_recent_titles failed; treating as not duplicate")
        return False
    for existing_title in recent_titles:
        similarity = ratio(new_title.lower(), existing_title.lower())
        if similarity >= DEDUP_THRESHOLD:
            return True
    return False
