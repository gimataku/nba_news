import calendar
import json
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from config import BATCH_INTERVAL_HOURS, SCHEDULER_POLL_MIN
from db import crud
from fetcher.rss import fetch_rss
from fetcher.score import fetch_score
from processor.claude_client import process_article
from processor.dedup import is_duplicate
from processor.filter import is_spurs_related

logger = logging.getLogger(__name__)


def _elapsed_hours(iso_str: str) -> float:
    """ISO8601文字列から現在時刻までの経過時間（時間）を返す。"""
    try:
        past = datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - past).total_seconds() / 3600
    except (ValueError, TypeError):
        return float("inf")


def _parse_pub_date(entry) -> datetime | None:
    """feedparser entry の published_parsed を UTC datetime に変換する。"""
    parsed = getattr(entry, "published_parsed", None)
    if not parsed:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
    except Exception:
        return None


def run_batch() -> None:
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%dT%H:%M:%S")
    fetched_count = 0
    error_message = None

    # ① 月次リセットチェック
    current_month = now.strftime("%Y-%m")
    if crud.get_setting("api_reset_month") != current_month:
        crud.set_setting("api_limit_exceeded", "false")
        crud.set_setting("api_reset_month", current_month)
        logger.info("Monthly API limit reset: %s", current_month)

    # ② RSS取得
    entries, source_name, is_fallback = fetch_rss()

    if not entries:
        error_message = "All RSS sources failed"
        logger.error(error_message)
        crud.save_fetch_log({
            "executed_at":   now_str,
            "source_used":   None,
            "is_fallback":   1,
            "fetched_count": 0,
            "error_message": error_message,
        })
        return

    logger.info(
        "RSS fetched: source=%s is_fallback=%s entries=%d",
        source_name, is_fallback, len(entries),
    )

    for entry in entries:
        # ③ 重複チェック
        link = entry.get("link", "").strip()
        if not link or crud.exists_article(link):
            continue

        title_original = entry.get("title", "").strip()

        # ③-2 重複チェック②：Levenshtein類似度チェック
        if is_duplicate(title_original, crud):
            pub_dt = _parse_pub_date(entry)
            published_at = pub_dt.strftime("%Y-%m-%dT%H:%M:%S") if pub_dt else None
            try:
                crud.save_article_as_duplicate({
                    "link":           link,
                    "title_original": title_original,
                    "title_ja":       title_original,
                    "summary_ja":     None,
                    "category":       None,
                    "is_spurs":       0,
                    "has_score":      0,
                    "is_duplicate":   1,
                    "score_data":     None,
                    "source":         source_name,
                    "published_at":   published_at,
                    "fetched_at":     now_str,
                })
                logger.info("Duplicate article skipped: %s", link)
            except Exception as exc:
                logger.error("DB save error for duplicate %s: %s", link, exc)
            continue

        # ④ Spursフィルタ
        is_spurs = is_spurs_related(entry)

        # ⑤ Claude API処理
        # API上限超過中は翻訳・保存をスキップ
        if crud.get_setting("api_limit_exceeded") == "true":
            continue

        description = entry.get("summary", "") or entry.get("description", "")
        result = process_article(title_original, description)

        if result is None:
            if crud.get_setting("api_limit_exceeded") == "true":
                # RateLimitError（429）→ スキップ（DB保存しない）
                continue
            else:
                # JSONDecodeError・バリデーション失敗等 → fallback値で保存
                result = {
                    "title_ja":  title_original,
                    "summary_ja": None,
                    "category":   None,
                    "has_score":  False,
                }

        # ⑥ スコア取得（has_score=True の記事のみ。gameカテゴリ廃止によりhas_score単独判定）
        score_data = None
        if result["has_score"]:
            pub_dt = _parse_pub_date(entry)
            if pub_dt:
                score = fetch_score(pub_dt)
                if score:
                    score_data = json.dumps(score)

        # ⑦ DB保存
        pub_dt = _parse_pub_date(entry)
        published_at = pub_dt.strftime("%Y-%m-%dT%H:%M:%S") if pub_dt else None

        article = {
            "link":           link,
            "title_original": title_original,
            "title_ja":       result["title_ja"],
            "summary_ja":     result["summary_ja"],
            "category":       result["category"],
            "is_spurs":       1 if is_spurs else 0,
            "has_score":      1 if result["has_score"] else 0,
            "score_data":     score_data,
            "source":         source_name,
            "published_at":   published_at,
            "fetched_at":     now_str,
        }
        try:
            crud.save_article(article)
            fetched_count += 1
        except Exception as exc:
            logger.error("DB save error for %s: %s", link, exc)

    # ⑧ 30日超データ削除
    deleted = crud.delete_old_articles()
    if deleted:
        logger.info("Deleted %d old articles", deleted)

    # ⑨ fetch_logs記録
    crud.save_fetch_log({
        "executed_at":   now_str,
        "source_used":   source_name,
        "is_fallback":   1 if is_fallback else 0,
        "fetched_count": fetched_count,
        "error_message": error_message,
    })

    # ⑩ last_fetched_atを現在時刻で更新
    crud.set_setting("last_fetched_at", now_str)
    logger.info("Batch completed: fetched=%d source=%s", fetched_count, source_name)


def check_and_run_batch() -> None:
    last_fetched_at = crud.get_setting("last_fetched_at")
    if last_fetched_at == "" or _elapsed_hours(last_fetched_at) >= BATCH_INTERVAL_HOURS:
        run_batch()


scheduler = BackgroundScheduler()
scheduler.add_job(check_and_run_batch, "interval", minutes=SCHEDULER_POLL_MIN)
