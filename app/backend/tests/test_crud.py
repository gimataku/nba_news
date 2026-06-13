"""T-03: 重複排除 / T-10: 30日超データ自動削除 / T-11: フェールオーバー記録"""
from datetime import datetime, timedelta, timezone

from db import crud
from db.models import Article, FetchLog


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _days_ago_str(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _insert_article(session, link: str, fetched_at: str, **kwargs):
    defaults = dict(
        title_original="Test Article",
        source="hoops_rumors",
    )
    defaults.update(kwargs)
    session.add(Article(link=link, fetched_at=fetched_at, **defaults))


# ── T-03 ──────────────────────────────────────────────────────────────────────

def test_t03_new_link():
    """T-03 ケース1: 未登録URLはFalseを返す"""
    assert crud.exists_article("https://example.com/brand-new") is False


def test_t03_existing_link(patch_db_session):
    """T-03 ケース2: 登録済みURLはTrueを返す"""
    _, TestSessionLocal = patch_db_session

    with TestSessionLocal() as session:
        _insert_article(session, "https://example.com/existing", _now_str())
        session.commit()

    assert crud.exists_article("https://example.com/existing") is True


# ── T-10 ──────────────────────────────────────────────────────────────────────

def test_t10_delete_old_articles(patch_db_session):
    """T-10: 31日前のデータのみ削除。30日前・29日前は残ること"""
    _, TestSessionLocal = patch_db_session

    with TestSessionLocal() as session:
        _insert_article(session, "https://example.com/a31", _days_ago_str(31))
        _insert_article(session, "https://example.com/a30", _days_ago_str(30))
        _insert_article(session, "https://example.com/a29", _days_ago_str(29))
        session.commit()

    deleted = crud.delete_old_articles()

    assert deleted == 1

    with TestSessionLocal() as session:
        remaining = [row.link for row in session.query(Article).all()]

    assert "https://example.com/a31" not in remaining
    assert "https://example.com/a30" in remaining
    assert "https://example.com/a29" in remaining


# ── T-11 ──────────────────────────────────────────────────────────────────────

def test_t11_failover_fetch_log(patch_db_session):
    """T-11: フェールオーバー発生時に fetch_logs に正しく記録されること"""
    _, TestSessionLocal = patch_db_session

    crud.save_fetch_log({
        "executed_at":   _now_str(),
        "source_used":   "hoops_wire",
        "is_fallback":   1,
        "fetched_count": 3,
        "error_message": None,
    })

    with TestSessionLocal() as session:
        log = session.query(FetchLog).first()

    assert log is not None
    assert log.source_used == "hoops_wire"
    assert log.is_fallback == 1
    assert log.error_message is None
