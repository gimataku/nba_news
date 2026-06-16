import os
import sqlite3

DB_PATH = os.getenv("DATABASE_URL", "nba_news.db")


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ① is_duplicate カラムを追加（既に存在する場合はスキップ）
    try:
        cur.execute(
            "ALTER TABLE articles ADD COLUMN is_duplicate INTEGER NOT NULL DEFAULT 0;"
        )
        print("[OK] ALTER TABLE articles ADD COLUMN is_duplicate")
    except sqlite3.OperationalError as e:
        print(f"[SKIP] already exists: {e}")

    # ② game_schedule テーブルを作成
    cur.execute("""
        CREATE TABLE IF NOT EXISTS game_schedule (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id       TEXT    NOT NULL UNIQUE,
            game_date     TEXT    NOT NULL,
            status        TEXT    NOT NULL,
            home_team     TEXT    NOT NULL,
            visitor_team  TEXT    NOT NULL,
            home_score    INTEGER,
            visitor_score INTEGER,
            has_score     INTEGER NOT NULL DEFAULT 0,
            fetched_at    TEXT    NOT NULL
        );
    """)
    print("[OK] CREATE TABLE IF NOT EXISTS game_schedule")

    # ③ users テーブルを作成
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT    NOT NULL UNIQUE,
            hashed_password TEXT    NOT NULL,
            created_at      TEXT    NOT NULL
        );
    """)
    print("[OK] CREATE TABLE IF NOT EXISTS users")

    # ④ is_duplicate インデックスを作成
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_is_duplicate ON articles(is_duplicate);"
    )
    print("[OK] CREATE INDEX IF NOT EXISTS idx_articles_is_duplicate")

    # ⑤ game_date インデックスを作成
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_game_schedule_game_date ON game_schedule(game_date);"
    )
    print("[OK] CREATE INDEX IF NOT EXISTS idx_game_schedule_game_date")

    conn.commit()
    conn.close()
    print("[DONE] migration complete")


if __name__ == "__main__":
    migrate()
