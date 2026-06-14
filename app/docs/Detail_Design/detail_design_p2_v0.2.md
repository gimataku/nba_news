# 詳細設計書（フェーズ2）

- **バージョン**: v0.2
- **ステータス**: Draft
- **作成日**: 2026-06-14
- **更新日**: 2026-06-14
- **対象**: NBAニュース翻訳アプリ 改修（フェーズ2）
- **参照**:
  - 要件定義書 フェーズ2 v0.12（`requirements_p2_v0.12.md`）
  - 基本設計書 フェーズ2 v0.5（`basic_design_p2_v0.5.md`）
  - 詳細設計書 フェーズ1 v0.3（`detail_design_v0.3.md`）※差分ベース

---

## 設計自己チェックリスト

| # | 確認内容 | 状態 |
|---|---|---|
| 1 | フェーズ1詳細設計書との差分が明示されているか | ✅ |
| 2 | 変更・新規の全モジュールに実装コードまたは擬似コードが記述されているか | ✅ |
| 3 | DBスキーマ変更（DDL）がbasic_design_p2_v0.5.mdと整合しているか | ✅ |
| 4 | エラーハンドリング方針が全新規モジュールに記述されているか | ✅ |
| 5 | JWT認証フローのセキュリティ面（トークン保存先・有効期限）が記述されているか | ✅ |
| 6 | 残課題D-04（game_schedule保持期間）・D-07（ページネーション）の扱いが明記されているか | ✅ |

---

## 1. バッチ処理（変更箇所）

### 1-1. run_batch()（バッチ処理本体・変更箇所）

フェーズ1の処理順序（detail_design_v0.3.md §1-2）を基本とし、以下を変更・追加する。

```
① 月次リセットチェック（変更なし）

② RSS取得（変更なし）

③ 重複チェック①：URL一致チェック（変更なし）
   取得記事のlink を articles テーブルと照合
   既存 → スキップ / 新規 → 処理継続

【新規】③-2 重複チェック②：Levenshtein類似度チェック（Dedup Processor）
   直近7日の articles.title_original（英語）に対してLevenshtein距離を計算
   類似度80%以上 → is_duplicate=True でDB保存 → 以降の処理をスキップ
   類似度80%未満 → 処理継続

④ Spursフィルタ（変更なし）

⑤ Claude API処理（プロンプト変更・バリデーション変更）
   → カテゴリ検証: trade_fa / draft / injury / column（フェーズ1のtrade/contract/game/columnから変更）
   → 返却値: summary_ja が800〜1200字（フェーズ1は300〜500字）
   → エラー時の処理はフェーズ1と同じ（title_ja=title_original・summary_ja=NULL・category=NULL）

⑥ Score Fetcher（試合スコア取得・変更なし）
   → has_score=True の記事のみ実行（フェーズ1と同じ判定ロジック。category="game"条件は廃止）

⑦ DB保存（is_duplicateカラム追加）
   → is_duplicate=False で保存（③-2通過後の記事は全てFalse）

⑧ 30日超データ削除（変更なし）

⑨ fetch_logs 記録（変更なし）

⑩ last_fetched_at 更新（変更なし）
```

### 1-2. C-05バッチ処理（新規・run_batch()と同周期）

RSSバッチとは独立して実行する（同一Schedulerから4時間ごとに呼び出す）。

```
【新規】C-05バッチ: fetch_game_schedule()

① BALLDONTLIE /v1/games エンドポイントを呼び出す
   params:
     start_date = 今日 - 1日（日本時間深夜開催の取り漏れ防止）
     end_date   = 今日 + 7日
     ※ team_ids[] は指定しない（全チームの試合日程を取得）

② 取得した全試合データを game_schedule テーブルに UPSERT（INSERT OR REPLACE）
   → game_id が UNIQUE キー・既存レコードの status/has_score/スコアを上書き

③ has_score フラグを設定
   status = "Final" または "In Progress" → has_score = True
   status = "Scheduled"               → has_score = False
```

---

## 2. 新規モジュール

### 2-1. Dedup Processor（`processor/dedup.py`・新規追加）

```python
from Levenshtein import ratio  # python-Levenshtein ライブラリ

DEDUP_THRESHOLD = 0.80     # 類似度閾値（80%以上で重複と判定）
DEDUP_WINDOW_DAYS = 7      # 比較対象の記事取得期間

def is_duplicate(new_title: str, db) -> bool:
    """
    直近7日の articles.title_original（英語）と新規記事タイトルを比較し
    類似度が80%以上の場合 True を返す。
    翻訳前（英語タイトル）で比較することでコスト削減と整合性を確保する。
    """
    recent_titles = db.get_recent_titles(days=DEDUP_WINDOW_DAYS)
    for existing_title in recent_titles:
        similarity = ratio(new_title.lower(), existing_title.lower())
        if similarity >= DEDUP_THRESHOLD:
            return True
    return False
```

**エラーハンドリング：**

| エラー種別 | 対応 |
|---|---|
| `Levenshtein` ライブラリ未インストール | requirements.txt に `python-Levenshtein` を追加 |
| DB接続エラー（`get_recent_titles`失敗） | 例外をキャッチしてログ出力・重複なし（False）として処理継続 |
| `new_title` が空文字 | False を返す（空タイトルは重複判定しない） |

---

### 2-2. Auth Module（`auth/`・新規追加）

#### 2-2-1. JWT処理（`auth/jwt.py`）

```python
from jose import jwt, JWTError
from datetime import datetime, timedelta
from config import SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS

# SECRET_KEY 未設定時は起動エラーとする（RED-01対応）
# config.py にてバリデーション済み（起動時に RuntimeError を送出）

def create_access_token(data: dict) -> str:
    """JWTトークンを発行する（有効期限30日）"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> str | None:
    """
    トークンを検証し、ユーザー名を返す。
    無効・期限切れの場合は None を返す。
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        return username
    except JWTError:
        return None
```

#### 2-2-2. ユーザー管理・Initスクリプト（`auth/users.py`）

```python
from passlib.context import CryptContext
from config import INIT_USERNAME, INIT_USER_PASSWORD  # YEL-01対応：config.py を唯一の設定ソースとして参照

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_user(db):
    """
    startup イベント時に呼び出す。
    usersテーブルが空の場合のみ、環境変数から初回ユーザーを作成する（冪等性あり）。
    USERNAME / USER_PASSWORD の未設定チェックは config.py にて起動時に実施済み。
    """
    if db.count_users() > 0:
        return   # 既にユーザーが存在する場合はスキップ

    hashed = pwd_context.hash(INIT_USER_PASSWORD)
    db.create_user(username=INIT_USERNAME, hashed_password=hashed)

def authenticate_user(username: str, password: str, db) -> bool:
    """ユーザー名とパスワードを検証する"""
    user = db.get_user(username)
    if not user:
        return False
    return pwd_context.verify(password, user["hashed_password"])
```

**エラーハンドリング：**

| エラー種別 | 対応 |
|---|---|
| `INIT_USERNAME` / `INIT_USER_PASSWORD` が未設定 | config.py にて起動時に `RuntimeError` → サービス起動失敗 |
| `SECRET_KEY` が未設定 | config.py にて起動時に `RuntimeError` → サービス起動失敗 |
| bcryptハッシュ化失敗 | 例外をキャッチしてログ出力・起動失敗 |
| DB接続エラー | 例外をそのまま raise |

---

### 2-3. Score Fetcher 拡張（`fetcher/score.py`・機能拡張）

フェーズ1の `fetch_score()` は変更なし。以下の関数を追加する。

```python
def fetch_game_schedule(start_date: str, end_date: str) -> list[dict]:
    """
    C-05バッチ用：BALLDONTLIE /v1/games から全チームの試合日程を取得する。
    Returns: 試合データのリスト（空リストの場合もあり）
    """
    url = "https://api.balldontlie.io/v1/games"
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "per_page": 100,    # 最大取得件数（1ページあたり）
    }
    headers = {"Authorization": f"Bearer {BALLDONTLIE_API_KEY}"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("data", [])

    except (requests.RequestException, KeyError) as e:
        logger.warning(f"BALLDONTLIE game_schedule fetch error: {e}")
        return []
```

**ページネーション注意：**
`per_page=100` で1週間分（最大約15試合/日 × 8日 ≒ 最大120件）の場合、1ページに収まらない可能性がある。詳細設計での確認事項（D-07として記録）。

---

## 3. 変更モジュール

### 3-1. Claude Client（`processor/claude_client.py`・プロンプト変更）

フェーズ1からの変更点のみ記述する（detail_design_v0.3.md §1-5 参照）。

#### プロンプト変更（確定版）

```python
USER_PROMPT_TEMPLATE = """以下のNBAニュース記事を処理してください。

タイトル: {title}
本文抜粋: {description}

以下のJSON形式で回答してください：
{{
  "title_ja": "日本語に翻訳した見出し（原文のニュアンスを保持）",
  "summary_ja": "800〜1200字の日本語要約",
  "category": "trade_fa または draft または injury または column",
  "has_score": true または false
}}

【分類ルール】
- trade_fa : トレード・移籍・FA・契約情報（フェーズ1の trade + contract を統合）
- draft    : ドラフト候補・指名・撤退情報
- injury   : インジャリーレポート・欠場・復帰情報
- column   : 試合分析・試合速報・スコア記事・選手評価・戦術・インタビュー・その他
             ※ 試合結果・スコアが主要情報の記事も column に分類すること（game カテゴリはなし）

【重要ルール】
- has_score は本文に具体的な得点数値が含まれる場合のみ true
- has_score=true のルールはカテゴリを問わず適用する（column でも true になりうる）
- JSON 以外の文字列を出力しないこと"""
```

#### バリデーション変更

```python
# フェーズ1
assert result["category"] in ("trade", "contract", "game", "column")

# フェーズ2（変更後）
assert result["category"] in ("trade_fa", "draft", "injury", "column")
```

---

### 3-2. DB CRUD 拡張（`db/crud.py`・変更・追加）

フェーズ1の関数はそのまま継承。以下の関数を追加・変更する。

#### 追加関数

| 関数名 | 内容 |
|---|---|
| `get_recent_titles(days)` | 直近n日の `articles.title_original` リストを返す（Dedup用） |
| `save_article_as_duplicate(article)` | `is_duplicate=True` で記事を保存（Dedup用） |
| `upsert_game_schedule(game)` | game_schedule テーブルに INSERT OR REPLACE する |
| `get_game_schedule(start_date, end_date)` | 試合日程を日付範囲で取得する |
| `delete_old_game_schedule()` | game_schedule テーブルの古いデータを削除する（D-04確定後に実装・保持期間は §8参照） |
| `count_users()` | users テーブルのレコード数を返す（init用） |
| `create_user(username, hashed_password)` | users テーブルに1件挿入する |
| `get_user(username)` | ユーザー名でユーザー情報を取得する |

#### 変更関数

```python
# フェーズ1
def get_articles(category, spurs_only, limit, offset):
    query = "SELECT * FROM articles"
    # ...

# フェーズ2（is_duplicate=Falseのみ返す）
def get_articles(category, spurs_only, limit, offset):
    query = "SELECT * FROM articles WHERE is_duplicate = 0"
    # category / spurs_only フィルタは従来通り
```

---

### 3-3. API Server（`api/routes.py`・認証追加・エンドポイント変更）

#### JWTミドルウェア（依存性注入）

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Authorization ヘッダーが存在しない場合：FastAPI HTTPBearer が HTTP 403 を返す（YEL-03対応）
    トークンが無効・期限切れの場合：HTTP 401 を返す
    """
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return username
```

#### 新規・変更エンドポイント

```python
# 新規: POST /api/auth/login（認証不要）
# セキュリティ注記: パスワードはHTTPS（TLS）経由でのみ送信される。
# Renderは自動的にHTTPをHTTPSにリダイレクトする（basic_design_p2_v0.5.md §2-1参照）。
# ブルートフォース対策: なし（設計判断・リスク受け入れ）→ §7参照
@router.post("/auth/login")
async def login(body: LoginBody):
    """
    ユーザー名・パスワードを検証してJWTトークンを返す。
    GETは不可（URLにパスワードが露出しRenderのアクセスログに残るリスク）。
    """
    if not authenticate_user(body.username, body.password, db):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": body.username})
    return {"access_token": token, "token_type": "bearer"}

# 変更: GET /api/news（旧 /api/articles・JWT認証追加・カテゴリ変更）
@router.get("/news")
async def get_news(
    category: str = "all",    # all / trade_fa / draft / injury / column
    spurs_only: bool = False,
    limit: int = Query(50, le=100),
    offset: int = 0,
    current_user: str = Depends(get_current_user),   # JWT認証必須
):
    articles = crud.get_articles(category, spurs_only, limit, offset)
    return {
        "articles": [{"source_url": a["link"], **a} for a in articles],
        "total": len(articles),
        "api_limit_exceeded": crud.get_setting("api_limit_exceeded") == "true",
    }

# 変更: GET /api/status（JWT認証追加）
@router.get("/status")
async def get_status(current_user: str = Depends(get_current_user)):
    ...  # 実装はフェーズ1と同じ

# 変更: GET /api/settings・PUT /api/settings（JWT認証追加）
@router.get("/settings")
async def get_settings(current_user: str = Depends(get_current_user)):
    ...

@router.put("/settings")
async def update_settings(body: SettingsBody, current_user: str = Depends(get_current_user)):
    ...

# 新規: GET /api/schedule（JWT認証必須）
@router.get("/schedule")
async def get_schedule(
    start_date: str,   # YYYY-MM-DD
    end_date: str,     # YYYY-MM-DD
    current_user: str = Depends(get_current_user),
):
    """C-05タブ用。game_scheduleテーブルから試合日程を返す。"""
    games = crud.get_game_schedule(start_date, end_date)
    return {"games": games}
```

**エンドポイント変更対応表：**

| フェーズ1 | フェーズ2 | 変更内容 |
|---|---|---|
| `GET /api/articles` | `GET /api/news` | パス変更・JWT追加・カテゴリ変更 |
| `GET /api/status` | `GET /api/status` | JWT追加のみ |
| `GET /api/settings` | `GET /api/settings` | JWT追加のみ |
| `PUT /api/settings` | `PUT /api/settings` | JWT追加のみ |
| `POST /api/fetch` | `POST /api/fetch` | JWT追加のみ |
| —（新規） | `POST /api/auth/login` | 新規（認証不要） |
| —（新規） | `GET /api/schedule` | 新規（JWT必須） |

---

## 4. DBスキーマ変更（DDL）

フェーズ1のDDL（detail_design_v0.3.md §2）を基本とし、以下を変更・追加する。

### 4-1. articles テーブル（変更）

```sql
-- フェーズ2: is_duplicate カラムを追加
ALTER TABLE articles ADD COLUMN is_duplicate INTEGER NOT NULL DEFAULT 0;

-- インデックス追加
CREATE INDEX idx_articles_is_duplicate ON articles(is_duplicate);

-- category の取りうる値: trade_fa / draft / injury / column / NULL
-- ※ DDL上のCHECK制約はなし（JSONエラー時NULLになるため）
-- ※ フェーズ1のtrade/contract/game/columnは廃止
```

### 4-2. game_schedule テーブル（新規追加）

```sql
CREATE TABLE game_schedule (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id       TEXT    NOT NULL UNIQUE,   -- BALLDONTLIEのゲームID（UPSERTキー）
    game_date     TEXT    NOT NULL,           -- 試合日 YYYY-MM-DD
    status        TEXT    NOT NULL,           -- "Scheduled" / "In Progress" / "Final"
    home_team     TEXT    NOT NULL,           -- ホームチーム略称
    visitor_team  TEXT    NOT NULL,           -- アウェイチーム略称
    home_score    INTEGER,                    -- ホームチームスコア（未終了はNULL）
    visitor_score INTEGER,                    -- アウェイチームスコア（未終了はNULL）
    has_score     INTEGER NOT NULL DEFAULT 0, -- 0 or 1（Final/In Progress は 1）
    fetched_at    TEXT    NOT NULL            -- 取得日時 ISO8601
);

CREATE INDEX idx_game_schedule_game_date ON game_schedule(game_date);
```

### 4-3. users テーブル（新規追加）

```sql
CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE,
    hashed_password TEXT    NOT NULL,
    created_at      TEXT    NOT NULL   -- ISO8601
);
```

### 4-4. app_settings テーブル（変更なし）

フェーズ1のDDL・初期データを継承。`spoiler_guard_enabled` は全体ON/OFFの単一フラグとして維持。

---

## 5. フロントエンド詳細設計（変更箇所）

### 5-1. 認証フロー（`auth/` 新規追加）

```javascript
// hooks/useAuth.js（新規）
// セキュリティ方針（YEL-04・GRN-04対応）:
//   - トークンはメモリ（Reactステート）に保持する（D-06確定）
//   - セキュリティ強度: メモリ保持 > sessionStorage > localStorage
//   - メモリ保持を採用する理由: XSSによるトークン窃取リスクがない（最もセキュア）
//   - トレードオフ: ページリロードでログアウトになる
//   - 家族利用（1〜2名、同一デバイスで継続利用）の範囲では許容する
//   - 通信はすべてHTTPS（TLS）経由（RenderがHTTP→HTTPSを自動リダイレクト）

export function useAuth() {
    const [token, setToken] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    const login = async (username, password) => {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        if (!res.ok) throw new Error("ログインに失敗しました");
        const data = await res.json();
        setToken(data.access_token);
        setIsAuthenticated(true);
        return data.access_token;
    };

    const logout = () => {
        setToken(null);
        setIsAuthenticated(false);
    };

    return { token, isAuthenticated, login, logout };
}
```

### 5-2. useNews フック変更（`hooks/useNews.js`）

フェーズ1（detail_design_v0.3.md §3-1）からの変更点のみ記述する。

```javascript
// フェーズ2での変更点

// 1. APIエンドポイント変更: /api/articles → /api/news
const res = await fetch(`/api/news?${params}`, {
    headers: { "Authorization": `Bearer ${token}` },  // JWT追加
});

// 2. タブリストとAPIカテゴリを分離（YEL-02対応）
//    TAB_LIST: 画面タブの定義（"schedule"タブを含む）
//    API_CATEGORIES: /api/news?category= のパラメータとして有効な値（"schedule"を含まない）
const TAB_LIST = ["all", "trade_fa", "draft", "schedule", "injury", "column"];
const API_CATEGORIES = ["all", "trade_fa", "draft", "injury", "column"];
// ※ "schedule"タブがアクティブな場合は useNews ではなく useSchedule フックを使用する。
//    useNews に category="schedule" を渡さないことで /api/news?category=schedule という
//    無意味なリクエストを防ぐ。

// 3. ネタバレ防止OFF→ON戻し（F-05b対応）
const resetSpoiler = (id) => {
    setRevealedIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
    });
};
```

### 5-3. SpoilerOverlay 変更（`components/SpoilerOverlay.jsx`）

フェーズ1（detail_design_v0.3.md §3-3）からの変更点：
- F-05b：「スコアを表示」→「スコアを隠す」ボタンを追加（ON戻し対応）
- 適用条件変更：全カテゴリの `has_score=true` に適用

```jsx
// フェーズ2: needsSpoiler の判定変更
// フェーズ1: (article.category === "game" || article.has_score) && !isRevealed
// フェーズ2: article.has_score && !isRevealed（全カテゴリに適用）
const needsSpoiler = spoilerGuard && article.has_score && !isRevealed;

// F-05b: 展開後にぼかしへ戻せるボタンを追加
{isRevealed && article.has_score && (
    <button
        onClick={() => onHide(article.id)}
        className="text-xs text-gray-400 underline mt-1"
    >
        スコアを隠す
    </button>
)}
```

### 5-4. 新規コンポーネント

#### LoginForm.jsx

```jsx
export function LoginForm({ onLogin }) {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError]       = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await onLogin(username, password);
        } catch {
            setError("ユーザー名またはパスワードが正しくありません");
        }
    };

    return (
        <form onSubmit={handleSubmit} className="max-w-sm mx-auto mt-20 p-6 border rounded-lg">
            <h1 className="text-lg font-bold mb-4">NBA News JP</h1>
            <input type="text"     value={username} onChange={e => setUsername(e.target.value)}
                   placeholder="ユーザー名" className="w-full border p-2 mb-2 rounded" />
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                   placeholder="パスワード"   className="w-full border p-2 mb-4 rounded" />
            {error && <p className="text-red-500 text-sm mb-2">{error}</p>}
            <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
                ログイン
            </button>
        </form>
    );
}
```

#### GameSchedule.jsx（F-05b対応・GRN-03）

試合日程タブ（C-05）にも F-05b（スコアを隠す）を適用する。
要件定義書 F-05b の「スコアを表示後に隠す」はニュース記事だけでなく試合日程にも適用する（一貫性のため）。

```jsx
export function GameSchedule({ token }) {
    const [games, setGames] = useState([]);

    useEffect(() => {
        const today = new Date().toISOString().split("T")[0];
        const nextWeek = new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0];
        fetch(`/api/schedule?start_date=${today}&end_date=${nextWeek}`, {
            headers: { "Authorization": `Bearer ${token}` },
        })
            .then(r => r.json())
            .then(d => setGames(d.games));
    }, [token]);

    return (
        <div>
            {games.map(game => (
                <GameRow key={game.game_id} game={game} />
            ))}
        </div>
    );
}

function GameRow({ game }) {
    const [revealed, setRevealed] = useState(false);

    return (
        <div className="border rounded p-3 mb-2 flex justify-between items-center">
            <span>{game.visitor_team} @ {game.home_team}</span>
            <span className="text-sm text-gray-500">{game.game_date}</span>

            {game.has_score && !revealed ? (
                // ネタバレ防止: スコアを表示ボタン
                <button onClick={() => setRevealed(true)}
                        className="text-xs bg-blue-100 px-2 py-1 rounded">
                    スコアを表示
                </button>
            ) : revealed && game.home_score != null ? (
                // 展開後: スコア表示 + スコアを隠すボタン（F-05b対応）
                <div className="flex flex-col items-end">
                    <span className="font-mono">
                        {game.visitor_score} - {game.home_score}
                    </span>
                    <button onClick={() => setRevealed(false)}
                            className="text-xs text-gray-400 underline mt-1">
                        スコアを隠す
                    </button>
                </div>
            ) : (
                // Scheduled: 試合日程のみ表示
                <span className="text-gray-400 text-xs">{game.status}</span>
            )}
        </div>
    );
}
```

---

## 6. config.py 変更（フェーズ2追加分）

```python
# フェーズ2追加分

# JWT設定
SECRET_KEY = os.getenv("SECRET_KEY", "")
# SECRET_KEY 未設定バリデーション（RED-01対応）
# 空文字キーでもjose/HS256はエラーなく動作するが、署名が実質無効化されるため
# 起動時に明示的にエラーを送出してサイレント障害を防ぐ
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY が未設定です。openssl rand -hex 32 で生成し環境変数に設定してください。"
    )

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# ユーザー設定（起動時initスクリプト用）
INIT_USERNAME      = os.getenv("USERNAME", "")
INIT_USER_PASSWORD = os.getenv("USER_PASSWORD", "")

# INIT_USERNAME / INIT_USER_PASSWORD 未設定バリデーション
if not INIT_USERNAME or not INIT_USER_PASSWORD:
    raise RuntimeError(
        "USERNAME / USER_PASSWORD が未設定です。環境変数に設定してください。"
    )

# C-05バッチ設定
GAME_SCHEDULE_START_OFFSET_DAYS = -1   # start_date = 今日 - 1日
GAME_SCHEDULE_END_OFFSET_DAYS   =  7   # end_date   = 今日 + 7日
BALLDONTLIE_PER_PAGE = 100             # 1リクエストあたりの最大取得件数

# Dedup設定
DEDUP_THRESHOLD   = 0.80   # Levenshtein類似度閾値（80%以上で重複）
DEDUP_WINDOW_DAYS = 7      # 比較対象期間（日）
```

> **設計方針（RED-01対応）：** SECRET_KEY・USERNAME・USER_PASSWORD のバリデーションは `config.py` のモジュール読み込み時（起動時）に一括実施する。各モジュール（jwt.py・users.py）は config.py をインポートするだけでよい（YEL-01対応）。バリデーション漏れを防ぐ単一責任の原則に基づく設計。

---

## 7. エラーハンドリング設計（フェーズ2追加・変更）

フェーズ1のエラーハンドリング（detail_design_v0.3.md §5）を基本とし、以下を追加する。

| エラー種別 | 発生箇所 | 対応 | ユーザー通知 |
|---|---|---|---|
| **Authorization ヘッダーなし** | API Server（FastAPI HTTPBearer） | **HTTP 403 を返す**（FastAPI HTTPBearer の標準挙動） | フロントエンドでログイン画面にリダイレクト |
| JWT検証失敗（無効・期限切れ） | API Server（get_current_user） | HTTP 401 を返す | フロントエンドでログイン画面にリダイレクト |
| ログイン失敗（認証失敗） | POST /api/auth/login | HTTP 401 を返す | LoginForm にエラーメッセージ表示 |
| `SECRET_KEY` 未設定 | config.py（起動時） | 起動失敗（RuntimeError） | — |
| `USERNAME` / `USER_PASSWORD` 未設定 | config.py（起動時） | 起動失敗（RuntimeError） | — |
| Levenshtein計算エラー | Dedup Processor | False を返し処理継続 | なし（ログ記録のみ） |
| BALLDONTLIE game_schedule 取得失敗 | C-05バッチ | 空リストで処理終了・ログ記録 | なし |
| game_schedule UPSERT失敗 | db/crud.py | エラーログ出力・バッチ継続 | なし |
| **ブルートフォース（連続ログイン試行）** | POST /api/auth/login | **対策なし（設計判断・リスク受け入れ）** | — |

> **ブルートフォース対策の設計判断（YEL-05対応）：** slowapi 等によるレート制限は追加しない。理由：①家族利用（1〜2名）のため標的型攻撃リスクが低い、②bcryptの計算コストにより総当たりが低速、③強力なパスワードの使用で実質的なリスクを許容範囲内に抑えられる。レート制限が必要な場合は詳細設計 v0.3 で対応する。

---

## 8. 残課題（詳細設計で確定が必要なもの）

| # | 課題 | 詳細設計での確定内容 |
|---|---|---|
| D-04 | game_schedule の保持期間 | articles と同様30日か、別途定義するか。`delete_old_game_schedule()` の実装方針に直結（関数は§3-2に仮定義済み） |
| D-07 | game_schedule ページネーション | BALLDONTLIE `per_page=100` で1週間分が収まるか確認。収まらない場合はカーソルページネーション実装が必要 |

> **確定済み：**
> - D-06（JWTトークン保存先）→ **メモリ保持（Reactステート・useState）で確定**（§5-1参照）。セキュリティ強度最高・ページリロードでログアウトの挙動は家族利用範囲で許容。

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v0.1 | 2026-06-14 | 初版作成。フェーズ1詳細設計書（v0.3）を差分ベースとしてフェーズ2の変更点のみを記述。新規モジュール（Dedup Processor・Auth Module）・Score Fetcher拡張・API認証追加・DBスキーマ変更・フロントエンド変更・config.py追加・エラーハンドリング追加・残課題D-04/D-06/D-07を記載 |
| v0.2 | 2026-06-14 | レビュー指摘（🔴1件・🟡5件・🟢4件）を全10件反映。①config.pyにSECRET_KEY未設定時のRuntimeError起動バリデーションを追加（RED-01）、②auth/users.pyをos.getenvから`from config import`参照に変更し設定の一元化（YEL-01）、③TAB_LISTとAPI_CATEGORIESを分離し"schedule"を/api/newsのcategoryパラメータから除外（YEL-02）、④§7エラーハンドリング表にHTTP 403（Authorizationヘッダーなし）を追記（YEL-03）、⑤D-06をメモリ保持（useState）で確定・§8残課題から削除・§5-1にセキュリティ根拠を追記（YEL-04）、⑥ブルートフォース対策なしを設計判断として§7に明示（YEL-05・A案）、⑦自己チェックリストを全件✅に更新（GRN-01）、⑧delete_old_game_schedule()を§3-2 CRUD追加関数一覧に追記（GRN-02）、⑨GameRow.jsxにF-05b（スコアを隠す）ボタンを追加（GRN-03）、⑩§5-1 useAuth.jsにHTTPS前提の注記を追記（GRN-04） |
