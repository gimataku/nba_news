import os
from dotenv import load_dotenv

load_dotenv()

# APIキー
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY", "")

# Claude API設定
CLAUDE_MODEL      = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS = 2048  # summary_ja が800〜1200字に増加したためフェーズ2で拡張（設計書明記なし・技術的補正）
CLAUDE_INTERVAL   = 1.0  # リクエスト間インターバル（秒）

# バッチ設定
BATCH_INTERVAL_HOURS = 4   # 前回取得からの最小間隔（時間）
SCHEDULER_POLL_MIN   = 10  # APSchedulerのポーリング間隔（分）

# データ保持
DATA_RETENTION_DAYS = 30

# Spurs設定
SPURS_TEAM_ID = 27
SPURS_KEYWORDS = [
    "spurs",
    "san antonio",
    "san antonio spurs",
    "wembanyama",
    "stephon castle",
]

# RSSソース設定
RSS_SOURCES = [
    {
        "name": "hoops_rumors",
        "url": "https://hoopsrumors.com/feed",
        "timeout": (5, 10),
        "retry": 2,
    },
    {
        "name": "hoops_wire",
        "url": "https://hoopswire.com/feed",
        "timeout": (5, 10),
        "retry": 2,
    },
    {
        "name": "the_cold_wire",
        "url": "https://thecoldwire.com/sports/nba/feed",
        "timeout": (5, 10),
        "retry": 2,
    },
]

# 重複チェック設定
DEDUP_THRESHOLD   = 0.80  # Levenshtein類似度閾値（80%以上で重複）
DEDUP_WINDOW_DAYS = 7     # 比較対象期間（日）

# フェーズ2拡張用（現在はNBAのみ）
SPORT = "NBA"
