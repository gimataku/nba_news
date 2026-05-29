import os
import re
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.models import Article, FetchLog, SessionLocal
from db.crud import get_latest_fetch_log, get_setting

JST = timezone(timedelta(hours=9))

MONTHLY_COST_LIMIT = 20.0
INPUT_TOKEN_COST_PER_M = 1.00   # $1.00 / 1M tokens
OUTPUT_TOKEN_COST_PER_M = 5.00  # $5.00 / 1M tokens
AVG_INPUT_TOKENS = 800
AVG_OUTPUT_TOKENS = 400

LOG_TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_jst() -> datetime:
    return datetime.now(JST)


def _to_jst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(JST)


def _fmt_jst(dt: datetime) -> str:
    return _to_jst(dt).strftime("%Y-%m-%d %H:%M JST")


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _format_elapsed(hours: float) -> str:
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes}分前"
    elif hours < 24:
        return f"{hours:.1f}時間前"
    else:
        days = int(hours / 24)
        remaining = hours % 24
        return f"{days}日{remaining:.0f}時間前"


def check_batch_status() -> None:
    print("【バッチ稼働】")

    last_fetched_at = get_setting("last_fetched_at")
    now_utc = _now_utc()

    if not last_fetched_at:
        print("  最終取得: 未取得 ⚠️")
    else:
        dt = _parse_iso(last_fetched_at)
        if dt is None:
            print(f"  最終取得: パース失敗 ({last_fetched_at}) ⚠️")
        else:
            elapsed_hours = (now_utc - dt).total_seconds() / 3600
            elapsed_str = _format_elapsed(elapsed_hours)
            jst_str = _fmt_jst(dt)
            if elapsed_hours <= 8:
                print(f"  最終取得: {jst_str} ({elapsed_str}) ✅")
            else:
                print(f"  最終取得: {jst_str} ({elapsed_str}) ⚠️ 警告")

    log = get_latest_fetch_log()
    if log is None:
        print("  使用ソース: 取得ログなし")
    else:
        source = log["source_used"] or "不明"
        if log["is_fallback"]:
            print(f"  使用ソース: {source}（フェールオーバーあり）⚠️")
        else:
            print(f"  使用ソース: {source}（フェールオーバーなし）✅")

    api_limit = get_setting("api_limit_exceeded")
    if api_limit == "true":
        print("  API上限超過: あり ⚠️")
    else:
        print("  API上限超過: なし ✅")

    print()


def check_article_stats() -> None:
    print("【直近24時間の記事】")

    cutoff = (_now_utc() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

    with SessionLocal() as session:
        total = session.query(Article).filter(Article.fetched_at >= cutoff).count()

        categories = ["trade", "contract", "game", "column"]
        cat_counts = {
            cat: session.query(Article)
            .filter(Article.fetched_at >= cutoff, Article.category == cat)
            .count()
            for cat in categories
        }

        spurs_count = (
            session.query(Article)
            .filter(Article.fetched_at >= cutoff, Article.is_spurs == 1)
            .count()
        )

    print(f"  総取得数: {total}件")
    cat_line = " / ".join(f"{cat}: {cat_counts[cat]}件" for cat in categories)
    print(f"  {cat_line}")
    print(f"  Spurs関連: {spurs_count}件")
    print()


def check_error_logs() -> None:
    print("【エラーログ（直近24時間）】")

    log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "logs", "nba_news.log"
    )

    if not os.path.exists(log_path):
        print("  ログなし")
        print()
        return

    # ログのタイムスタンプはローカル時刻（JST）で記録される
    cutoff_naive = datetime.now() - timedelta(hours=24)

    warning_count = 0
    error_count = 0
    error_lines: list[str] = []

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    continue

                m = LOG_TIMESTAMP_RE.match(line)
                if m:
                    try:
                        line_dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                        if line_dt < cutoff_naive:
                            continue
                    except ValueError:
                        pass

                if "[WARNING]" in line:
                    warning_count += 1
                elif "[ERROR]" in line:
                    error_count += 1
                    if len(error_lines) < 5:
                        error_lines.append(line)

    except OSError as e:
        print(f"  ログ読み込みエラー: {e}")
        print()
        return

    print(f"  WARNING: {warning_count}件")
    if error_count == 0:
        print("  ERROR: 0件 ✅")
    else:
        print(f"  ERROR: {error_count}件 ⚠️")
        for err_line in error_lines:
            print(f"    {err_line}")

    print()


def check_monthly_cost() -> None:
    print("【月次コスト試算（直近30日）】")

    cutoff = (_now_utc() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")

    with SessionLocal() as session:
        result = (
            session.query(func.sum(FetchLog.fetched_count))
            .filter(FetchLog.executed_at >= cutoff)
            .scalar()
        )

    total_count = result or 0

    input_cost = total_count * AVG_INPUT_TOKENS / 1_000_000 * INPUT_TOKEN_COST_PER_M
    output_cost = total_count * AVG_OUTPUT_TOKENS / 1_000_000 * OUTPUT_TOKEN_COST_PER_M
    total_cost = input_cost + output_cost
    usage_pct = (total_cost / MONTHLY_COST_LIMIT) * 100

    print(f"  取得記事数: {total_count}件")
    cost_str = f"${total_cost:.2f} / ${MONTHLY_COST_LIMIT:.2f}（{usage_pct:.1f}%）"
    if usage_pct >= 80:
        print(f"  推定コスト: {cost_str} ⚠️ 警告")
    else:
        print(f"  推定コスト: {cost_str} ✅")

    print()


def main() -> None:
    now_jst = _now_jst()
    print("====================================")
    print("NBA News JP - 監視レポート")
    print(now_jst.strftime("%Y-%m-%d %H:%M JST"))
    print("====================================")

    try:
        check_batch_status()
    except Exception as e:
        print(f"  [ERROR] バッチ稼働チェック失敗: {e}\n")

    try:
        check_article_stats()
    except Exception as e:
        print(f"  [ERROR] 記事統計チェック失敗: {e}\n")

    try:
        check_error_logs()
    except Exception as e:
        print(f"  [ERROR] ログチェック失敗: {e}\n")

    try:
        check_monthly_cost()
    except Exception as e:
        print(f"  [ERROR] コスト試算失敗: {e}\n")

    print("====================================")


if __name__ == "__main__":
    main()
