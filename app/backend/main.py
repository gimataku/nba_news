import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from auth.users import init_user
from db import crud
from db.models import init_db
from scheduler import check_and_run_batch, scheduler

# logsディレクトリの自動作成（起動時に存在しない場合に生成）
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/nba_news.log"),
    ],
)

logger = logging.getLogger(__name__)

app = FastAPI(title="NBA News JP")

# CORS設定（ローカル開発時は localhost:5173、本番はALLOWED_ORIGINS環境変数で指定）
_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
_origins = [o.strip() for o in _origins_env.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/healthz")
def healthz():
    """認証不要のヘルスチェック（Renderのヘルスチェックパスに使用）"""
    return {"status": "ok"}


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    logger.info("DB initialized")
    init_user(crud)
    logger.info("Initial user check completed")
    scheduler.start()
    logger.info("Scheduler started")
    check_and_run_batch()


@app.on_event("shutdown")
def shutdown_event() -> None:
    scheduler.shutdown()
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", 8000)),
        reload=False,
    )
