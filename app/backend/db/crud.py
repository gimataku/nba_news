from datetime import datetime, timedelta, timezone

from sqlalchemy import desc

from .models import AppSetting, Article, FetchLog, SessionLocal


def get_setting(key: str) -> str:
    with SessionLocal() as session:
        row = session.get(AppSetting, key)
        return row.value if row else ""


def set_setting(key: str, value: str) -> None:
    with SessionLocal() as session:
        row = session.get(AppSetting, key)
        if row:
            row.value = value
        else:
            session.add(AppSetting(key=key, value=value))
        session.commit()


def exists_article(link: str) -> bool:
    with SessionLocal() as session:
        return session.query(Article).filter_by(link=link).first() is not None


def save_article(article: dict) -> None:
    with SessionLocal() as session:
        session.add(Article(**article))
        session.commit()


def get_articles(
    category: str = "all",
    spurs_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    with SessionLocal() as session:
        q = session.query(Article)
        if category != "all":
            q = q.filter(Article.category == category)
        if spurs_only:
            q = q.filter(Article.is_spurs == 1)
        rows = (
            q.order_by(desc(Article.fetched_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [_article_to_dict(r) for r in rows]


def get_recent_titles(days: int) -> list[str]:
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).strftime("%Y-%m-%dT%H:%M:%S")
    with SessionLocal() as session:
        rows = (
            session.query(Article.title_original)
            .filter(Article.fetched_at >= cutoff)
            .order_by(desc(Article.fetched_at))
            .all()
        )
        return [r.title_original for r in rows]


def save_article_as_duplicate(article: dict) -> None:
    with SessionLocal() as session:
        session.add(Article(**article))
        session.commit()


def delete_old_articles() -> int:
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=30)
    ).strftime("%Y-%m-%dT%H:%M:%S")
    with SessionLocal() as session:
        deleted = (
            session.query(Article)
            .filter(Article.fetched_at < cutoff)
            .delete(synchronize_session=False)
        )
        session.commit()
        return deleted


def save_fetch_log(log: dict) -> None:
    with SessionLocal() as session:
        session.add(FetchLog(**log))
        session.commit()


def get_latest_fetch_log() -> dict | None:
    with SessionLocal() as session:
        row = (
            session.query(FetchLog)
            .order_by(desc(FetchLog.executed_at))
            .first()
        )
        if row is None:
            return None
        return {
            "executed_at":   row.executed_at,
            "source_used":   row.source_used,
            "is_fallback":   bool(row.is_fallback),
            "fetched_count": row.fetched_count,
            "error_message": row.error_message,
        }


# --- helper ---

def _article_to_dict(row: Article) -> dict:
    return {
        "id":             row.id,
        "link":           row.link,
        "title_original": row.title_original,
        "title_ja":       row.title_ja,
        "summary_ja":     row.summary_ja,
        "category":       row.category,
        "is_spurs":       bool(row.is_spurs),
        "has_score":      bool(row.has_score),
        "score_data":     row.score_data,
        "source":         row.source,
        "published_at":   row.published_at,
        "fetched_at":     row.fetched_at,
    }
