import logging
import os

import uvicorn
from fastapi import FastAPI

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


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    logger.info("DB initialized")
    scheduler.start()
    logger.info("Scheduler started")
    check_and_run_batch()


@app.on_event("shutdown")
def shutdown_event() -> None:
    scheduler.shutdown()
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
