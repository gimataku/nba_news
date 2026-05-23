# 詳細設計書

- **バージョン**: v0.3
- **ステータス**: Draft
- **作成日**: 2026-05-10
- **対象**: NBAニュース翻訳アプリ（個人利用）
- **参照**:
  - 要件定義書 v0.6（`requirements_v0.6.md`）※セクション5の参照先がrisk_report_v0.4.mdと古い。v0.7更新時にrisk_report_v0.5.mdへ修正すること
  - 基本設計書 v0.4（`basic_design_v0.4.md`）

---

## 1. モジュール別処理フロー

### 1-1. Scheduler（`scheduler.py`）

```python
# 起動時・復帰時に呼び出されるチェック関数
def check_and_run_batch():
    last_fetched_at = db.get_setting("last_fetched_at")  # "" or ISO8601

    # 初回起動または4時間経過で実行
    if last_fetched_at == "" or elapsed_hours(last_fetched_at) >= 4:
        run_batch()

# APSchedulerで10分ごとにcheck_and_run_batchを呼び出す
# （厳密な時刻指定ではなく経過時間で判定）
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_run_batch, "interval", minutes=10)
scheduler.start()
```

**処理順序：**

1. `last_fetched_at` を `app_settings` から取得
2. `""` または 現在時刻との差が4時間以上 → `run_batch()` 実行
3. `run_batch()` 完了後、`last_fetched_at` を現在時刻で更新

---

### 1-2. run_batch()（バッチ処理本体）

```
① 月次リセットチェック
   現在月 ≠ api_reset_month の場合:
     api_limit_exceeded = "false"
     api_reset_month = 現在月

② RSS取得（fetcher/rss.py）
   Hoops Rumors → Hoops Wire → The Cold Wire NBA の順でフェールオーバー

③ 重複チェック
   取得記事のlink を articles テーブルと照合
   既存 → スキップ / 新規 → 処理継続

④ Spursフィルタ（processor/filter.py）
   categoryタグ → title/description の順でキーワードマッチ

⑤ Claude API処理（processor/claude_client.py）
   api_limit_exceeded が "true" の場合はスキップ（DBに保存しない）
   各記事を1リクエストで翻訳・要約・分類

   → process_article() が None を返した場合の分岐：
     【RateLimitError（429）の場合】
       api_limit_exceeded = "true" に更新済み
       当該記事をスキップ（DBに保存しない）

     【JSONDecodeError・バリデーション失敗・その他APIエラーの場合】
       title_ja   = title_original（英語見出しをそのまま格納）
       summary_ja = NULL
       category   = NULL
       has_score  = False
       → DBに保存（⑦へ進む）

⑥ スコア取得（fetcher/score.py）
   category="game" または has_score=True の記事のみ実行

⑦ DB保存（db/crud.py）
   articles テーブルへ一括保存

⑧ 30日超データ削除
   fetched_at < (現在時刻 - 30日) の記事を削除

⑨ fetch_logs 記録
   実行結果・使用ソース・エラー有無を記録

⑩ last_fetched_at を現在時刻で更新
```

---

### 1-3. RSS Fetcher（`fetcher/rss.py`）

```python
RSS_SOURCES = [
    {
        "name": "hoops_rumors",
        "url": "https://hoopsrumors.com/feed",
        "timeout": (5, 10),   # (接続タイムアウト, 読み取りタイムアウト) 秒
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

def fetch_rss_source(source: dict) -> list:
    """
    requestsでコンテンツを取得しfeedparserでパースする。
    feedparser.parse()はタイムアウトを直接制御できないため、
    requests.get()でタイムアウトを制御してからfeedparserに渡す。
    """
    response = requests.get(
        source["url"],
        headers={"User-Agent": "NBANewsJP/1.0"},
        timeout=source["timeout"],   # (接続タイムアウト5秒, 読み取りタイムアウト10秒) が有効になる
    )
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    return feed.entries

def fetch_rss() -> tuple[list[dict], str, bool]:
    """
    Returns: (articles, source_name, is_fallback)
    フェールオーバー発生時は is_fallback=True
    全ソース失敗時は ([], "", True) を返し、呼び出し元でエラーログ記録
    """
    for i, source in enumerate(RSS_SOURCES):
        for attempt in range(source["retry"]):
            try:
                entries = fetch_rss_source(source)
                if entries:
                    return entries, source["name"], (i > 0)
            except Exception:
                time.sleep(1)
    return [], "", True
```

**フェールオーバー判定（いずれか1つで次ソースへ）：**
- 接続タイムアウト（5秒）← `requests.get()` で制御
- 読み取りタイムアウト（10秒）← `requests.get()` で制御
- HTTP 4xx / 5xx レスポンス（`raise_for_status()` で検知）
- XML パースエラー（`feedparser.parse()` で検知）
- `feed.entries` が空（記事0件）

---

### 1-4. Spursフィルタ（`processor/filter.py`）

```python
SPURS_KEYWORDS = [
    "spurs", "san antonio", "san antonio spurs",
    "wembanyama", "stephon castle",   # 主要選手（設定ファイルで管理）
]

def is_spurs_related(entry: dict) -> bool:
    """
    優先順位1: <category>タグにキーワードが含まれるか
    優先順位2: <title> + <description> にキーワードが含まれるか
    """
    # categoryタグの取得（feedparserでは entry.tags として取得）
    categories = [tag.term.lower() for tag in getattr(entry, "tags", [])]
    for keyword in SPURS_KEYWORDS:
        if any(keyword in cat for cat in categories):
            return True

    # フォールバック: title + description テキスト検索
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    return any(keyword in text for keyword in SPURS_KEYWORDS)
```

**キーワードリストの管理方針：**
- `config.py` の `SPURS_KEYWORDS` リストで一元管理
- 選手名は主要選手のみ（フランチャイズプレイヤー相当）
- シーズン移籍等に応じて手動更新

---

### 1-5. Claude Client（`processor/claude_client.py`）

#### プロンプト（確定版）

```python
SYSTEM_PROMPT = """あなたはNBAニュースの翻訳・要約・分類アシスタントです。
必ずJSON形式のみで回答してください。マークダウンや説明文は不要です。"""

USER_PROMPT_TEMPLATE = """以下のNBAニュース記事を処理してください。

タイトル: {title}
本文抜粋: {description}

以下のJSON形式で回答してください：
{{
  "title_ja": "日本語に翻訳した見出し（原文のニュアンスを保持）",
  "summary_ja": "300〜500字の日本語要約",
  "category": "trade または contract または game または column",
  "has_score": true または false
}}

【分類ルール】
- trade: 移籍・トレード噂・交渉・成立報道（交渉段階も含む）
- contract: サイン・契約延長・FA動向・契約金額の報道
- game: 試合当日〜翌日の速報・スコアを主要情報として含む記事
- column: 試合分析・選手評価・戦術考察・インタビュー等（スコアが引用で含まれる場合も column）

【重要ルール】
- category が "game" の場合、summary_ja にスコア・得点・勝敗を含めないこと
- has_score は本文に具体的な得点数値が含まれる場合のみ true
- JSON 以外の文字列を出力しないこと"""
```

#### 呼び出し処理

```python
def process_article(title: str, description: str) -> dict | None:
    """
    Returns: {"title_ja": str, "summary_ja": str, "category": str, "has_score": bool}
    失敗時: None（呼び出し元でスキップ処理）
    """
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    title=title,
                    description=description[:1000]  # 最大1000文字に制限
                )
            }]
        )
        raw = response.content[0].text.strip()
        # ```json ... ``` フェンスが含まれる場合は除去
        raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.MULTILINE)
        result = json.loads(raw)

        # バリデーション
        assert result["category"] in ("trade", "contract", "game", "column")
        assert isinstance(result["has_score"], bool)
        return result

    except anthropic.RateLimitError:
        # 429エラー: API上限超過
        db.set_setting("api_limit_exceeded", "true")
        return None

    except (json.JSONDecodeError, KeyError, AssertionError):
        # JSON解析失敗・バリデーションエラー: スキップ
        logger.warning(f"Claude response parse error: {title}")
        return None

    finally:
        time.sleep(1)  # レートリミット対策インターバル
```

#### エラーハンドリング方針

| エラー種別 | 対応 |
|---|---|
| `RateLimitError`（429） | `api_limit_exceeded="true"` に更新。以降の記事はスキップ |
| `JSONDecodeError` | 当該記事をスキップ。`title_ja=title_original`・`summary_ja=NULL` で保存 |
| `AssertionError`（バリデーション失敗） | 同上 |
| その他の`APIError` | 当該記事をスキップ。エラーをログ出力 |
| タイムアウト | 最大2回リトライ後にスキップ |

---

### 1-6. Score Fetcher（`fetcher/score.py`）

```python
SPURS_TEAM_ID = 27  # BALLDONTLIEにおけるSpursのチームID

def fetch_score(pub_date: datetime) -> dict | None:
    """
    pubDateから対象日を決定し、Spursの試合スコアを取得する。
    Returns: スコアデータ(dict) または None（試合なし）
    """
    # 対象日の決定
    if pub_date.hour < 12:
        target_date = (pub_date - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date = pub_date.strftime("%Y-%m-%d")

    url = "https://api.balldontlie.io/v1/games"
    params = {
        "team_ids[]": SPURS_TEAM_ID,
        "start_date": target_date,
        "end_date": target_date,
    }
    headers = {"Authorization": f"Bearer {BALLDONTLIE_API_KEY}"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        games = response.json().get("data", [])

        if not games:
            return None  # 試合なし → score_data=NULL

        game = games[0]
        return {
            "game_id": game["id"],
            "home_team": game["home_team"]["abbreviation"],
            "visitor_team": game["visitor_team"]["abbreviation"],
            "home_score": game["home_team_score"],
            "visitor_score": game["visitor_team_score"],
            "status": game["status"],
            "period": game.get("period", 0),
            "quarters": [],   # 詳細クォータースコアは別エンドポイントのため省略
        }

    except (requests.RequestException, KeyError):
        logger.warning(f"BALLDONTLIE fetch error for date: {target_date}")
        return None
```

---

### 1-7. DB操作（`db/crud.py`）

#### 主要関数一覧

| 関数名 | 内容 |
|---|---|
| `get_setting(key)` | `app_settings` から設定値を取得 |
| `set_setting(key, value)` | `app_settings` に設定値を保存 |
| `exists_article(link)` | `articles` に同一リンクが存在するか確認（重複排除） |
| `save_article(article)` | `articles` に1件保存 |
| `get_articles(category, spurs_only, limit, offset)` | 記事一覧を条件付きで取得 |
| `delete_old_articles()` | 30日超データを削除 |
| `save_fetch_log(log)` | `fetch_logs` にバッチ実行結果を記録 |

---

### 1-8. APIサーバー（`api/routes.py`）

#### エンドポイント詳細

```python
# GET /api/articles
@router.get("/articles")
async def get_articles(
    category: str = "all",       # all / trade / contract / game / column
    spurs_only: bool = False,
    limit: int = Query(50, le=100),
    offset: int = 0,
):
    articles = crud.get_articles(category, spurs_only, limit, offset)
    api_limit = crud.get_setting("api_limit_exceeded") == "true"

    # source_urlはDBのlinkカラムをそのまま返す（致命-2対応：source_urlカラム廃止のため）
    articles_response = [
        {**article, "source_url": article["link"]}
        for article in articles
    ]

    return {
        "articles": articles_response,
        "total": len(articles_response),
        "api_limit_exceeded": api_limit,
    }

# GET /api/status
@router.get("/status")
async def get_status():
    log = crud.get_latest_fetch_log()
    return {
        "last_fetched_at": crud.get_setting("last_fetched_at"),
        "source_used": log.source_used if log else None,
        "is_fallback": log.is_fallback if log else False,
        "api_limit_exceeded": crud.get_setting("api_limit_exceeded") == "true",
    }

# POST /api/fetch（手動バッチトリガー）
@router.post("/fetch")
async def trigger_fetch(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_batch)
    return {"message": "バッチ処理を開始しました"}

# GET /api/settings
@router.get("/settings")
async def get_settings():
    return {
        "spoiler_guard_enabled": crud.get_setting("spoiler_guard_enabled") == "true",
        "spurs_filter_enabled": crud.get_setting("spurs_filter_enabled") == "true",
    }

# PUT /api/settings
@router.put("/settings")
async def update_settings(body: SettingsBody):
    if body.spoiler_guard_enabled is not None:
        crud.set_setting("spoiler_guard_enabled", str(body.spoiler_guard_enabled).lower())
    if body.spurs_filter_enabled is not None:
        crud.set_setting("spurs_filter_enabled", str(body.spurs_filter_enabled).lower())
    return {"message": "設定を更新しました"}
```

---

## 2. DBスキーマ（詳細）

### 2-1. articlesテーブル（DDL）

```sql
CREATE TABLE articles (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    link             TEXT    NOT NULL UNIQUE,   -- 重複排除キー兼元記事URL（APIレスポンスではsource_urlとして返す）
    title_original   TEXT    NOT NULL,           -- 英語見出し（原文）
    title_ja         TEXT,                       -- 翻訳済み見出し（エラー時はtitle_originalと同値・NULLにならない設計）
    summary_ja       TEXT,                       -- 日本語要約（API上限時・JSONエラー時はNULL）
    category         TEXT,                       -- trade / contract / game / column（JSONエラー時はNULL）
    is_spurs         INTEGER NOT NULL DEFAULT 0, -- 0 or 1
    has_score        INTEGER NOT NULL DEFAULT 0, -- 0 or 1
    score_data       TEXT,                       -- JSON文字列（試合なし or 非対象はNULL）
    source           TEXT    NOT NULL,           -- hoops_rumors / hoops_wire / the_cold_wire
    published_at     TEXT,                       -- 記事公開日時 ISO8601
    fetched_at       TEXT    NOT NULL            -- 取得日時 ISO8601
);

CREATE INDEX idx_articles_category  ON articles(category);
CREATE INDEX idx_articles_is_spurs  ON articles(is_spurs);
CREATE INDEX idx_articles_fetched   ON articles(fetched_at);
```

> **設計方針（致命-2対応）：** `source_url` カラムは `link` と同値のため削除。APIレスポンス生成時に `link` を `source_url` キーとして返す（例：`"source_url": article.link`）。

### 2-2. fetch_logsテーブル（DDL）

```sql
CREATE TABLE fetch_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    executed_at    TEXT    NOT NULL,   -- バッチ実行日時 ISO8601
    source_used    TEXT,               -- hoops_rumors / hoops_wire / the_cold_wire / NULL(失敗)
    is_fallback    INTEGER NOT NULL DEFAULT 0,  -- 0 or 1
    fetched_count  INTEGER NOT NULL DEFAULT 0,  -- 新規取得件数
    error_message  TEXT                         -- エラー詳細（正常時はNULL）
);
```

### 2-3. app_settingsテーブル（DDL）

```sql
CREATE TABLE app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 初期データ
INSERT INTO app_settings VALUES ('spoiler_guard_enabled', 'true');
INSERT INTO app_settings VALUES ('spurs_filter_enabled',  'false');
INSERT INTO app_settings VALUES ('last_fetched_at',       '');
INSERT INTO app_settings VALUES ('api_limit_exceeded',    'false');
INSERT INTO app_settings VALUES ('api_reset_month',       '');
```

---

## 3. フロントエンド詳細設計

### 3-1. useNews フック（`hooks/useNews.js`）

```javascript
export function useNews() {
    const [articles, setArticles] = useState([]);
    const [apiStatus, setApiStatus] = useState({
        api_limit_exceeded: false,
        is_fallback: false,
        last_fetched_at: null,
    });
    const [selectedCategory, setSelectedCategory] = useState("all");
    const [spursOnly, setSpursOnly] = useState(false);
    const [spoilerGuard, setSpoilerGuard] = useState(true);
    const [revealedIds, setRevealedIds] = useState(new Set());
    const [loading, setLoading] = useState(false);

    // 記事取得
    const fetchArticles = useCallback(async () => {
        setLoading(true);
        const params = new URLSearchParams({
            category: selectedCategory,
            spurs_only: spursOnly,
            limit: 50,
        });
        const [articlesRes, statusRes] = await Promise.all([
            fetch(`/api/articles?${params}`),
            fetch("/api/status"),
        ]);
        const data = await articlesRes.json();
        const status = await statusRes.json();
        setArticles(data.articles);
        setApiStatus(status);
        setLoading(false);
    }, [selectedCategory, spursOnly]);

    // 設定変更時にAPIへ同期
    const toggleSpoilerGuard = async () => {
        const next = !spoilerGuard;
        setSpoilerGuard(next);
        await fetch("/api/settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ spoiler_guard_enabled: next }),
        });
    };

    // スコア展開
    const revealScore = (id) => {
        setRevealedIds(prev => new Set([...prev, id]));
    };

    // Spursフィルタ切替（API同期あり）
    const toggleSpursFilter = async () => {
        const next = !spursOnly;
        setSpursOnly(next);
        await fetch("/api/settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ spurs_filter_enabled: next }),
        });
    };

    useEffect(() => { fetchArticles(); }, [fetchArticles]);

    return {
        articles, apiStatus, selectedCategory, spursOnly,
        spoilerGuard, revealedIds, loading,
        setSelectedCategory, toggleSpursFilter,
        toggleSpoilerGuard, revealScore, fetchArticles,
    };
}
```

### 3-2. NewsCard コンポーネント（`components/NewsCard.jsx`）

```jsx
export function NewsCard({ article, spoilerGuard, isRevealed, onReveal }) {
    const needsSpoiler = spoilerGuard &&
        (article.category === "game" || article.has_score) &&
        !isRevealed;

    return (
        <div className="border rounded-lg p-4 mb-3 bg-white">
            {/* カテゴリバッジ */}
            <CategoryBadge category={article.category} />

            {/* 見出し */}
            <h2 className="font-semibold text-sm mt-1 mb-2">
                {article.title_ja || article.title_original}
            </h2>

            {/* 要約またはネタバレ防止 */}
            {needsSpoiler ? (
                <SpoilerOverlay onReveal={() => onReveal(article.id)} />
            ) : (
                <p className="text-sm text-gray-600 mb-2">
                    {article.summary_ja || "（翻訳データなし）"}
                    {/* スコア表示（展開後） */}
                    {isRevealed && article.score_data && (
                        <ScoreDisplay scoreData={article.score_data} />
                    )}
                </p>
            )}

            {/* ソースリンク */}
            <div className="text-xs text-gray-400">
                {article.source} · {formatRelativeTime(article.published_at)} ·{" "}
                <a href={article.source_url} target="_blank" rel="noopener noreferrer"
                   className="text-blue-500 underline">
                    原文を読む
                </a>
            </div>
        </div>
    );
}
```

### 3-3. SpoilerOverlay コンポーネント（`components/SpoilerOverlay.jsx`）

```jsx
export function SpoilerOverlay({ onReveal }) {
    return (
        <div className="relative mb-2">
            {/* ぼかし表示のダミーテキスト */}
            <p className="text-sm text-gray-600 select-none"
               style={{ filter: "blur(8px)", userSelect: "none" }}>
                スコアや試合結果の情報がここに表示されます。
            </p>
            {/* 解除ボタン */}
            <div className="absolute inset-0 flex items-center justify-center">
                <button
                    onClick={onReveal}
                    className="bg-blue-600 text-white text-xs px-3 py-1 rounded-full
                               hover:bg-blue-700 transition-colors"
                >
                    スコアを表示
                </button>
            </div>
        </div>
    );
}
```

---

## 4. config.py（定数・環境変数管理）

```python
import os
from dotenv import load_dotenv

load_dotenv()

# APIキー
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY", "")

# Claude API設定
CLAUDE_MODEL       = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS  = 1024
CLAUDE_INTERVAL    = 1.0   # リクエスト間インターバル（秒）

# バッチ設定
BATCH_INTERVAL_HOURS = 4    # 前回取得からの最小間隔（時間）
SCHEDULER_POLL_MIN   = 10   # APSchedulerのポーリング間隔（分）

# データ保持
DATA_RETENTION_DAYS = 30

# Spurs設定
SPURS_TEAM_ID = 27
SPURS_KEYWORDS = [
    "spurs", "san antonio", "san antonio spurs",
    "wembanyama", "stephon castle",
]

# RSSソース設定
RSS_SOURCES = [
    {"name": "hoops_rumors",  "url": "https://hoopsrumors.com/feed",                 "timeout": (5, 10), "retry": 2},
    {"name": "hoops_wire",    "url": "https://hoopswire.com/feed",                   "timeout": (5, 10), "retry": 2},
    {"name": "the_cold_wire", "url": "https://thecoldwire.com/sports/nba/feed",      "timeout": (5, 10), "retry": 2},
]

# フェーズ2拡張用（現在はNBAのみ）
SPORT = "NBA"
```

---

## 5. エラーハンドリング設計

### 5-1. エラー種別と対応方針

| エラー種別 | 発生箇所 | 対応 | ユーザー通知 |
|---|---|---|---|
| RSS全ソース取得失敗 | RSS Fetcher | バッチをスキップ・fetch_logsにエラー記録 | バナー表示（「ニュース取得に失敗しました」） |
| RSSタイムアウト | RSS Fetcher（requests.get） | タイムアウト検知後リトライ→フェールオーバー | なし（フェールオーバーが成功すれば通常動作） |
| Claude API 429 | Claude Client | `api_limit_exceeded="true"`・翻訳スキップ | バナー表示（「API上限に達しました」） |
| Claude APIその他エラー | Claude Client | 当該記事スキップ・英語見出しのみ保存 | なし（ログ記録のみ） |
| JSON解析失敗 | Claude Client | 当該記事スキップ | なし（ログ記録のみ） |
| BALLDONTLIE取得失敗 | Score Fetcher | `score_data=NULL`・「スコアを表示」ボタン非表示 | なし |
| DB書き込みエラー | DB CRUD | エラーログ出力・バッチ継続 | なし |
| フロントエンドAPIエラー | useNews フック | エラーメッセージをUI表示 | インライン表示 |

### 5-2. ロギング方針

```python
import logging
import os

# logsディレクトリの自動作成（起動時に存在しない場合に生成）
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),                        # コンソール出力
        logging.FileHandler("logs/nba_news.log"),       # ファイル出力
    ]
)
```

- ログファイル：`logs/nba_news.log`
- ローテーション：手動（個人利用のため自動ローテーション不要）
- ログレベル：INFO（通常動作）/ WARNING（スキップ・フェールオーバー）/ ERROR（致命的エラー）

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v0.1 | 2026-05-10 | 初版作成 |
| v0.2 | 2026-05-10 | レビュー指摘（致命2件・改善4件・軽微3件）を全件反映。①RSS Fetcherをrequests経由でコンテンツ取得後にfeedparserへ渡す方式に変更しタイムアウト制御を有効化（致命-1）、②articlesテーブルからsource_urlカラムを削除しAPIレスポンス生成時にlinkをsource_urlとして返す方式に変更（致命-2）、③run_batch()⑤にNone返却時の分岐（RateLimitError→スキップ/その他エラー→英語見出しで保存）を明記（改善-1）、④useNewsフックのsetSpursOnlyをtoggleSpursFilterに変更しAPI同期処理を追加（改善-2）、⑤main.pyにos.makedirs("logs", exist_ok=True)を追加（改善-4）、⑥title_jaのNULL設計意図をDDLコメントで明記（軽微-1）、⑦requirements参照先の注記を追加（軽微-3） |
| v0.3 | 2026-05-10 | 再レビュー指摘（新規2件）を全件反映。①GET /api/articlesのレスポンス生成コードに`"source_url": article["link"]`の明示を追記しDBのsource_urlカラム廃止との整合性を確保（新規-1）、②DDLのtitle_ja行にコメントを追記（新規-2） |
