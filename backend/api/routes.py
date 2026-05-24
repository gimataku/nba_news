from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel

from db import crud
from scheduler import run_batch

router = APIRouter()


class SettingsBody(BaseModel):
    spoiler_guard_enabled: bool | None = None
    spurs_filter_enabled: bool | None = None


@router.get("/articles")
async def get_articles(
    category: str = "all",
    spurs_only: bool = False,
    limit: int = Query(50, le=100),
    offset: int = 0,
):
    articles = crud.get_articles(category, spurs_only, limit, offset)
    api_limit = crud.get_setting("api_limit_exceeded") == "true"

    # source_urlはDBのlinkカラムをそのまま返す（source_urlカラムは存在しないため）
    articles_response = [
        {**article, "source_url": article["link"]}
        for article in articles
    ]

    return {
        "articles": articles_response,
        "total": len(articles_response),
        "api_limit_exceeded": api_limit,
    }


@router.get("/status")
async def get_status():
    log = crud.get_latest_fetch_log()  # dict | None
    return {
        "last_fetched_at":   crud.get_setting("last_fetched_at"),
        "source_used":       log["source_used"] if log else None,
        "is_fallback":       log["is_fallback"] if log else False,
        "api_limit_exceeded": crud.get_setting("api_limit_exceeded") == "true",
    }


@router.post("/fetch")
async def trigger_fetch(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_batch)
    return {"message": "バッチ処理を開始しました"}


@router.get("/settings")
async def get_settings():
    return {
        "spoiler_guard_enabled": crud.get_setting("spoiler_guard_enabled") == "true",
        "spurs_filter_enabled":  crud.get_setting("spurs_filter_enabled") == "true",
    }


@router.put("/settings")
async def update_settings(body: SettingsBody):
    if body.spoiler_guard_enabled is not None:
        crud.set_setting("spoiler_guard_enabled", str(body.spoiler_guard_enabled).lower())
    if body.spurs_filter_enabled is not None:
        crud.set_setting("spurs_filter_enabled", str(body.spurs_filter_enabled).lower())
    return {"message": "設定を更新しました"}
