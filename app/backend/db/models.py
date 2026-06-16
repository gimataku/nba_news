import os

from sqlalchemy import Column, Index, Integer, Text, create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Article(Base):
    __tablename__ = "articles"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    link           = Column(Text, nullable=False, unique=True)  # 重複排除キー兼元記事URL
    title_original = Column(Text, nullable=False)
    title_ja       = Column(Text)  # エラー時はtitle_originalと同値・NULLにならない設計
    summary_ja     = Column(Text)  # API上限時・JSONエラー時はNULL
    category       = Column(Text)  # trade/contract/game/column（JSONエラー時はNULL）
    is_spurs       = Column(Integer, nullable=False, default=0)  # 0 or 1
    has_score      = Column(Integer, nullable=False, default=0)  # 0 or 1
    is_duplicate   = Column(Integer, nullable=False, default=0)  # 0 or 1
    score_data     = Column(Text)   # JSON文字列（試合なし or 非対象はNULL）
    source         = Column(Text, nullable=False)  # hoops_rumors/hoops_wire/the_cold_wire
    published_at   = Column(Text)   # 記事公開日時 ISO8601
    fetched_at     = Column(Text, nullable=False)  # 取得日時 ISO8601

    __table_args__ = (
        Index("idx_articles_category",     "category"),
        Index("idx_articles_is_spurs",     "is_spurs"),
        Index("idx_articles_fetched",      "fetched_at"),
        Index("idx_articles_is_duplicate", "is_duplicate"),
    )


class FetchLog(Base):
    __tablename__ = "fetch_logs"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    executed_at   = Column(Text, nullable=False)   # バッチ実行日時 ISO8601
    source_used   = Column(Text)                   # NULL=全ソース失敗
    is_fallback   = Column(Integer, nullable=False, default=0)  # 0 or 1
    fetched_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)                   # 正常時はNULL


class AppSetting(Base):
    __tablename__ = "app_settings"

    key   = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)


class GameSchedule(Base):
    __tablename__ = "game_schedule"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    game_id       = Column(Text, nullable=False, unique=True)  # BALLDONTLIEのゲームID（UPSERTキー）
    game_date     = Column(Text, nullable=False)               # YYYY-MM-DD
    status        = Column(Text, nullable=False)               # Scheduled / In Progress / Final
    home_team     = Column(Text, nullable=False)
    visitor_team  = Column(Text, nullable=False)
    home_score    = Column(Integer)                            # 未終了はNULL
    visitor_score = Column(Integer)                            # 未終了はNULL
    has_score     = Column(Integer, nullable=False, default=0) # 0 or 1（Final/In Progress は 1）
    fetched_at    = Column(Text, nullable=False)

    __table_args__ = (
        Index("idx_game_schedule_game_date", "game_date"),
    )


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    username        = Column(Text, nullable=False, unique=True)
    hashed_password = Column(Text, nullable=False)
    created_at      = Column(Text, nullable=False)


# --- DB初期化 ---

DB_PATH = os.getenv("DATABASE_URL", "nba_news.db")
engine  = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_INITIAL_SETTINGS = [
    ("spoiler_guard_enabled", "true"),
    ("spurs_filter_enabled",  "false"),
    ("last_fetched_at",       ""),
    ("api_limit_exceeded",    "false"),
    ("api_reset_month",       ""),
]


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        for key, value in _INITIAL_SETTINGS:
            if not session.get(AppSetting, key):
                session.add(AppSetting(key=key, value=value))
        session.commit()
