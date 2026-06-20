from datetime import datetime, timedelta, timezone

from sqlalchemy import desc

from config import DATA_RETENTION_DAYS
from .models import AppSetting, Article, FetchLog, GameSchedule, SessionLocal, User


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
        q = session.query(Article).filter(Article.is_duplicate == 0)
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


# --- users ---

def count_users() -> int:
    with SessionLocal() as session:
        return session.query(User).count()


def create_user(username: str, hashed_password: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    with SessionLocal() as session:
        session.add(User(username=username, hashed_password=hashed_password, created_at=now))
        session.commit()


def get_user(username: str) -> dict | None:
    with SessionLocal() as session:
        row = session.query(User).filter_by(username=username).first()
        if row is None:
            return None
        return {"username": row.username, "hashed_password": row.hashed_password}


# --- game_schedule ---

def upsert_game_schedule(game: dict) -> None:
    with SessionLocal() as session:
        row = session.query(GameSchedule).filter_by(game_id=game["game_id"]).first()
        if row:
            for key, value in game.items():
                setattr(row, key, value)
        else:
            session.add(GameSchedule(**game))
        session.commit()


def get_game_schedule(start_date: str, end_date: str) -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(GameSchedule)
            .filter(GameSchedule.game_date >= start_date)
            .filter(GameSchedule.game_date <= end_date)
            .order_by(GameSchedule.game_date)
            .all()
        )
        return [_game_schedule_to_dict(r) for r in rows]


def delete_old_game_schedule() -> int:
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=DATA_RETENTION_DAYS)
    ).strftime("%Y-%m-%dT%H:%M:%S")
    with SessionLocal() as session:
        deleted = (
            session.query(GameSchedule)
            .filter(GameSchedule.fetched_at < cutoff)
            .delete(synchronize_session=False)
        )
        session.commit()
        return deleted


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


def _game_schedule_to_dict(row: GameSchedule) -> dict:
    return {
        "id":           row.id,
        "game_id":      row.game_id,
        "game_date":    row.game_date,
        "status":       row.status,
        "home_team":    row.home_team,
        "visitor_team": row.visitor_team,
        "home_score":   row.home_score,
        "visitor_score": row.visitor_score,
        "has_score":    bool(row.has_score),
        "fetched_at":   row.fetched_at,
    }
