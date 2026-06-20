from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from auth.jwt import create_access_token, verify_token
from auth.users import authenticate_user
from db import crud
from scheduler import run_batch

router = APIRouter()

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Authorizationヘッダーなし → FastAPI HTTPBearerがHTTP 403を返す
    トークン無効・期限切れ → HTTP 401を返す
    """
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return username


class SettingsBody(BaseModel):
    spoiler_guard_enabled: bool | None = None
    spurs_filter_enabled: bool | None = None


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(body: LoginBody):
    """
    ユーザー名・パスワードを検証してJWTトークンを返す。
    GETは不可（URLにパスワードが露出しアクセスログに残るリスクのため）。
    """
    if not authenticate_user(body.username, body.password, crud):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": body.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/news")
async def get_news(
    category: str = "all",
    spurs_only: bool = False,
    limit: int = Query(50, le=100),
    offset: int = 0,
    current_user: str = Depends(get_current_user),
):
    """
    category: all / trade_fa / draft / injury / column
    is_duplicate=1の記事はレスポンスに含まれない（crud層で除外済み）。
    """
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


@router.get("/schedule")
async def get_schedule(
    start_date: str,
    end_date: str,
    current_user: str = Depends(get_current_user),
):
    """C-05タブ用。game_scheduleテーブルから試合日程を返す。"""
    games = crud.get_game_schedule(start_date, end_date)
    return {"games": games}


@router.get("/status")
async def get_status(current_user: str = Depends(get_current_user)):
    log = crud.get_latest_fetch_log()
    return {
        "last_fetched_at":    crud.get_setting("last_fetched_at"),
        "source_used":        log["source_used"] if log else None,
        "is_fallback":        log["is_fallback"] if log else False,
        "api_limit_exceeded": crud.get_setting("api_limit_exceeded") == "true",
    }


@router.post("/fetch")
async def trigger_fetch(
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    background_tasks.add_task(run_batch)
    return {"message": "バッチ処理を開始しました"}


@router.get("/settings")
async def get_settings(current_user: str = Depends(get_current_user)):
    return {
        "spoiler_guard_enabled": crud.get_setting("spoiler_guard_enabled") == "true",
        "spurs_filter_enabled":  crud.get_setting("spurs_filter_enabled") == "true",
    }


@router.put("/settings")
async def update_settings(
    body: SettingsBody,
    current_user: str = Depends(get_current_user),
):
    if body.spoiler_guard_enabled is not None:
        crud.set_setting("spoiler_guard_enabled", str(body.spoiler_guard_enabled).lower())
    if body.spurs_filter_enabled is not None:
        crud.set_setting("spurs_filter_enabled", str(body.spurs_filter_enabled).lower())
    return {"message": "設定を更新しました"}
