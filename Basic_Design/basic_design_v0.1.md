# 基本設計書

- **バージョン**: v0.1
- **ステータス**: Draft
- **作成日**: 2026-05-10
- **対象**: NBAニュース翻訳アプリ（個人利用）
- **参照**:
  - 要件定義書 v0.6（`requirements_v0.6.md`）
  - リスク調査レポート v0.5（`risk_report_v0.5.md`）
  - プロジェクト計画書 v0.3（`project_plan_v0.3.md`）

---

## 1. システム構成

### 1-1. 構成概要

本アプリは以下の3レイヤーで構成する。

```
┌──────────────────────────────────────────────────────────────┐
│                        外部サービス                           │
│  Hoops Rumors RSS   HoopsHype RSS   BALLDONTLIE API          │
│  （ニュース主軸）    （フェールオーバー）  （試合スコア）         │
│                           Claude API                          │
│                      （翻訳・要約・分類）                      │
└───────────────────────────┬──────────────────────────────────┘
                             │ HTTP
┌───────────────────────────▼──────────────────────────────────┐
│                      バックエンド（Python）                    │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ バッチ処理   │  │  API サーバー │  │   Claude Client    │  │
│  │ (Scheduler) │  │  (FastAPI)   │  │  (翻訳・要約・分類) │  │
│  └──────┬──────┘  └──────┬───────┘  └────────────────────┘  │
│         │                │                                    │
│  ┌──────▼────────────────▼───────────────────────────────┐   │
│  │                SQLite DB                               │   │
│  │  articles / fetch_logs / app_settings                  │   │
│  └────────────────────────────────────────────────────────┘   │
└───────────────────────────┬──────────────────────────────────┘
                             │ HTTP (localhost)
┌───────────────────────────▼──────────────────────────────────┐
│                  フロントエンド（React SPA）                   │
│          ニュース一覧 / フィルタ / ネタバレ防止 UI             │
└──────────────────────────────────────────────────────────────┘
```

### 1-2. コンポーネント一覧

| コンポーネント | 役割 | 技術 |
|---|---|---|
| Scheduler | 前回取得から4時間経過を検知し、バッチ処理を起動 | Python（APScheduler） |
| RSS Fetcher | Hoops Rumors（主軸）/ HoopsHype（フェールオーバー）からRSSを取得 | Python（feedparser） |
| Score Fetcher | BALLDONTLIE gamesエンドポイントから当日・前日の試合スコアを取得 | Python（requests） |
| Claude Client | 翻訳・要約・カテゴリ分類を1リクエストで実行 | Python（anthropic SDK） |
| API Server | フロントエンドへデータを提供するREST API | Python（FastAPI） |
| SQLite DB | 記事・取得ログ・アプリ設定を永続化 | SQLite3 |
| Frontend | ニュース一覧・フィルタ・ネタバレ防止UIを提供 | React + Vite |

---

## 2. 技術スタック

### 2-1. 選定一覧

| 区分 | 技術 | バージョン目安 | 選定理由 |
|---|---|---|---|
| バックエンド言語 | Python | 3.11以上 | Claude SDK・feedparser等の周辺ライブラリが充実 |
| APIフレームワーク | FastAPI | 0.110以上 | 軽量・非同期対応・自動ドキュメント生成 |
| スケジューラ | APScheduler | 3.x | cron非依存・Pythonプロセス内で動作・スリープ復帰対応 |
| RSSパーサー | feedparser | 6.x | Python標準的なRSSライブラリ |
| HTTPクライアント | requests / httpx | — | RSS取得・BALLDONTLIE API呼び出し |
| Claude SDK | anthropic | 最新安定版 | 公式SDK |
| DB | SQLite3 | （Python標準） | 追加インストール不要・個人利用規模に十分 |
| DBマイグレーション | Alembic | 1.x | スキーマ変更の管理 |
| フロントエンド | React + Vite | React 18 / Vite 5 | 軽量SPA・ローカル開発に最適 |
| UIライブラリ | Tailwind CSS | 3.x | 素早いUI構築 |
| パッケージ管理 | uv（Python）/ npm（JS） | — | 高速・モダン |

### 2-2. ディレクトリ構成

```
nba-news-jp/
├── backend/
│   ├── main.py              # FastAPIエントリーポイント（APIサーバー兼スケジューラ起動）
│   ├── scheduler.py         # APScheduler設定・バッチ起動ロジック
│   ├── fetcher/
│   │   ├── rss.py           # RSS取得・フェールオーバー制御
│   │   └── score.py         # BALLDONTLIE API取得
│   ├── processor/
│   │   ├── claude_client.py # Claude API呼び出し（翻訳・要約・分類）
│   │   └── filter.py        # Spursフィルタ（categoryタグ検索）
│   ├── db/
│   │   ├── models.py        # SQLAlchemyモデル定義
│   │   ├── crud.py          # DB操作（記事保存・取得・削除）
│   │   └── migrations/      # Alembicマイグレーションファイル
│   ├── api/
│   │   └── routes.py        # APIエンドポイント定義
│   └── config.py            # 環境変数・定数管理
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── NewsList.jsx
│   │   │   ├── NewsCard.jsx
│   │   │   ├── CategoryTabs.jsx
│   │   │   ├── FilterBar.jsx
│   │   │   ├── SpoilerOverlay.jsx
│   │   │   └── ApiBanner.jsx
│   │   └── hooks/
│   │       └── useNews.js
│   └── vite.config.js
├── .env                     # APIキー（Gitignore対象）
├── .env.example
├── setup.md                 # 環境構築手順書
└── README.md
```

---

## 3. データフロー

### 3-1. バッチ処理フロー（RSS取得〜DB保存）

```
[Scheduler]
    │ 前回取得から4時間以上経過？
    │ Yes
    ▼
[RSS Fetcher]
    │ Hoops Rumors RSS取得
    │   └─ 失敗（タイムアウト/HTTP 4xx/5xx）
    │         └─ HoopsHype RSS取得（フェールオーバー）
    │               └─ 失敗 → fetch_logs にエラー記録・処理中断
    │
    │ 成功: RSSアイテム一覧（title / description / link / pubDate / category）
    ▼
[重複チェック（DB）]
    │ articles テーブルに同一 link が存在するか確認
    │ 存在する → スキップ
    │ 存在しない → 処理継続
    ▼
[Filter: Spursチェック]
    │ <category>タグに「Spurs」「San Antonio」等が含まれるか確認
    │ → is_spurs フラグをセット（True/False）
    │ ※ Claude API不使用・追加コストなし
    ▼
[Claude Client: 翻訳・要約・分類（1リクエスト）]
    │ 入力: title + description（RSS抜粋）
    │ 出力（JSON）:
    │   - title_ja      : 翻訳済み見出し
    │   - summary_ja    : 日本語要約（300〜500字）
    │   - category      : トレード / 契約 / 試合結果 / コラム
    │   - has_score     : スコアが本文に含まれるか（Boolean）
    │   ※ 「試合結果」判定時はsummary_jaにスコアを含めない
    ▼
[Score Fetcher: BALLDONTLIE]
    │ category=「試合結果」 または has_score=True の記事のみ実行
    │ gamesエンドポイントから当日・前日の試合スコアを取得
    │ Spursの試合スコアを score_data（JSON）として保存
    ▼
[DB保存: articles テーブル]
    │ 記事データ一式を保存
    ▼
[古記事削除]
    │ 取得日から30日超の記事を自動削除
    ▼
[fetch_logs テーブル更新]
    　完了時刻・取得件数・エラー有無を記録
```

### 3-2. 画面表示フロー（フロントエンド）

```
[ブラウザ起動 / ページ読み込み]
    ▼
[GET /api/articles]
    │ クエリパラメータ:
    │   - category: all / trade / contract / game / column
    │   - spurs_only: true / false
    ▼
[APIサーバー → SQLite照会]
    ▼
[ニュース一覧表示]
    │
    ├─ カテゴリ=「試合結果」または has_score=True
    │   └─ ネタバレ防止ON時: 要約をぼかし表示 + [スコアを表示]ボタン
    │       └─ ボタンクリック時: score_data（BALLDONTLIE取得済み）を表示
    │
    └─ その他カテゴリ
        └─ 要約（summary_ja）をそのまま表示
```

---

## 4. フェールオーバー設計

Hoops Rumors1本化リスクへの対策として、以下のフェールオーバー機構を実装する。

### 4-1. フェールオーバー判定条件

| 条件 | 内容 |
|---|---|
| タイムアウト | 接続タイムアウト5秒 / 読み取りタイムアウト10秒 |
| HTTPエラー | 4xx / 5xx レスポンス |
| パースエラー | RSSのXML解析失敗 |
| 記事件数ゼロ | フィード取得成功だが記事が0件 |

### 4-2. フェールオーバー動作

```
Hoops Rumors取得試行（最大2回リトライ・1秒インターバル）
    └─ 失敗
        ↓
HoopsHype取得試行（最大2回リトライ）
    └─ 失敗
        ↓
fetch_logsにエラー記録
バッチ処理をスキップ（前回取得データをそのまま表示）
ヘッダーに「ニュース取得に失敗しました」バナーを表示
```

### 4-3. フェールオーバー情報のDB記録

`fetch_logs`テーブルに以下を記録し、運用状況を把握できるようにする。

| カラム | 内容 |
|---|---|
| source_used | 実際に使用したRSSソース名（hoops_rumors / hoopshype） |
| is_fallback | フェールオーバーが発生したか（Boolean） |
| error_message | エラー詳細 |

---

## 5. DBスキーマ（概要）

詳細なカラム定義は詳細設計書（`detail_design_v0.1.md`）で定義する。

### 5-1. テーブル一覧

| テーブル名 | 用途 |
|---|---|
| `articles` | 取得・翻訳済みニュース記事 |
| `fetch_logs` | バッチ実行履歴・エラーログ |
| `app_settings` | アプリ設定（ネタバレ防止ON/OFF等） |

### 5-2. articlesテーブル（主要カラム）

| カラム名 | 型 | 内容 |
|---|---|---|
| id | INTEGER PK | 自動採番 |
| link | TEXT UNIQUE | 元記事URL（重複排除キー） |
| title_original | TEXT | 元の見出し（英語） |
| title_ja | TEXT | 翻訳済み見出し |
| summary_ja | TEXT | 日本語要約（300〜500字） |
| category | TEXT | トレード / 契約 / 試合結果 / コラム |
| is_spurs | INTEGER | Spurs関連フラグ（0/1） |
| has_score | INTEGER | スコア含有フラグ（0/1） |
| score_data | TEXT | BALLDONTLIE取得スコア（JSON文字列） |
| source | TEXT | ソース名（hoops_rumors / hoopshype） |
| published_at | TEXT | 記事公開日時（ISO8601） |
| fetched_at | TEXT | 取得日時（ISO8601） |

### 5-3. fetch_logsテーブル（主要カラム）

| カラム名 | 型 | 内容 |
|---|---|---|
| id | INTEGER PK | 自動採番 |
| executed_at | TEXT | バッチ実行日時 |
| source_used | TEXT | 使用ソース名 |
| is_fallback | INTEGER | フェールオーバー発生フラグ |
| fetched_count | INTEGER | 新規取得件数 |
| error_message | TEXT | エラー詳細（正常時はNULL） |

### 5-4. app_settingsテーブル

| カラム名 | 型 | 内容 |
|---|---|---|
| key | TEXT PK | 設定キー |
| value | TEXT | 設定値 |

初期設定値:
- `spoiler_guard_enabled`: `"true"`
- `spurs_filter_enabled`: `"false"`（デフォルトは全チーム表示）
- `last_fetched_at`: `""` （バッチ実行時刻管理）

---

## 6. APIエンドポイント設計

### 6-1. エンドポイント一覧

| メソッド | パス | 内容 |
|---|---|---|
| GET | `/api/articles` | ニュース記事一覧取得 |
| GET | `/api/articles/{id}/score` | 指定記事のスコアデータ取得 |
| GET | `/api/settings` | アプリ設定取得 |
| PUT | `/api/settings` | アプリ設定更新 |
| GET | `/api/status` | 最終取得日時・フェールオーバー状況取得 |
| POST | `/api/fetch` | 手動バッチ実行トリガー |

### 6-2. GET /api/articles

**クエリパラメータ：**

| パラメータ | 型 | デフォルト | 内容 |
|---|---|---|---|
| category | string | all | all / trade / contract / game / column |
| spurs_only | boolean | false | Spursフィルタ |
| limit | integer | 50 | 最大取得件数 |
| offset | integer | 0 | ページングオフセット |

**レスポンス例：**

```json
{
  "articles": [
    {
      "id": 1,
      "title_ja": "スパーズ、ガードを獲得か",
      "summary_ja": "サンアントニオ・スパーズは...",
      "category": "trade",
      "is_spurs": true,
      "has_score": false,
      "source": "hoops_rumors",
      "source_url": "https://hoopsrumors.com/...",
      "published_at": "2026-05-10T07:30:00Z"
    }
  ],
  "total": 42,
  "api_limit_exceeded": false
}
```

### 6-3. GET /api/status

**レスポンス例：**

```json
{
  "last_fetched_at": "2026-05-10T07:30:00Z",
  "source_used": "hoops_rumors",
  "is_fallback": false,
  "api_limit_exceeded": false
}
```

---

## 7. Claude API連携設計

### 7-1. 呼び出し方針

- **1記事につき1リクエスト**で翻訳・要約・カテゴリ分類・スコア有無判定をまとめて実行
- **モデル**: claude-haiku-4-5（コスト最優先）
- **レスポンス形式**: JSON（構造化出力）
- **バッチ間インターバル**: 1秒/件（レートリミット対策）

### 7-2. プロンプト構成（概要）

```
[System]
あなたはNBAニュースの翻訳・要約・分類アシスタントです。
以下のルールに従って、JSON形式のみで回答してください。

[User]
以下のNBAニュース記事を処理してください。

タイトル: {title}
本文抜粋: {description}

以下のJSONを返してください：
{
  "title_ja": "日本語に翻訳した見出し",
  "summary_ja": "300〜500字の日本語要約（スコア・試合結果は含めない）",
  "category": "trade|contract|game|column のいずれか",
  "has_score": true|false  // 本文にスコアや得点が含まれるか
}

分類ルール:
- trade: 移籍・トレード噂・交渉・成立報道（交渉段階も含む）
- contract: サイン・契約延長・FA動向・契約金額の報道
- game: 試合当日〜翌日の速報・スコアを主要情報として含む記事
- column: 試合分析・選手評価・戦術考察・インタビュー等

重要: categoryが"game"の場合、summary_jaにスコアや勝敗を含めないこと。
```

### 7-3. API上限超過時の動作

```
Claude APIから429エラーが返った場合:
→ app_settings.api_limit_exceeded = "true" に更新
→ 当該記事の翻訳・要約をスキップ
→ title_jaにtitle_original（英語）をそのまま保存
→ summary_jaをNULLで保存
→ フロントエンドのヘッダーにバナーを表示
```

---

## 8. フロントエンド設計

### 8-1. 画面構成と主要コンポーネント

| コンポーネント | 役割 |
|---|---|
| `App.jsx` | 全体レイアウト・状態管理 |
| `ApiBanner.jsx` | API上限超過時・RSS取得失敗時のバナー表示 |
| `CategoryTabs.jsx` | カテゴリタブ（すべて/トレード/契約/試合結果/コラム） |
| `FilterBar.jsx` | チームフィルタ切替・ネタバレ防止ON/OFFトグル |
| `NewsList.jsx` | 記事カードのリスト表示 |
| `NewsCard.jsx` | 個別記事の表示（見出し・要約・リンク） |
| `SpoilerOverlay.jsx` | ネタバレ防止ぼかし表示・スコア展開UI |

### 8-2. 状態管理方針

ローカル状態（useState）で管理する。外部状態管理ライブラリ（Redux等）は使用しない。

| 状態 | 管理場所 | 内容 |
|---|---|---|
| articles | App.jsx | 取得済み記事一覧 |
| selectedCategory | App.jsx | 選択中カテゴリ |
| spursOnly | App.jsx | Spursフィルタ状態 |
| spoilerGuard | App.jsx | ネタバレ防止ON/OFF |
| revealedIds | App.jsx | スコアを展開した記事IDセット |
| apiStatus | App.jsx | API上限・取得エラー状態 |

### 8-3. ネタバレ防止UI仕様

- `has_score=true` または `category=game` の記事：要約テキストをCSSでぼかし（`filter: blur(8px)`）
- `revealedIds`に記事IDが含まれる場合：ぼかしを解除してスコアを表示
- ネタバレ防止OFF時：全記事を通常表示

---

## 9. セキュリティ・運用設計

### 9-1. APIキー管理

| キー | 保存場所 | 備考 |
|---|---|---|
| ANTHROPIC_API_KEY | `.env`（Gitignore対象） | バックエンドの環境変数として読み込む |
| BALLDONTLIE_API_KEY | `.env`（同上） | 無料ティア登録で取得 |

### 9-2. ローカルアクセス制限

FastAPIのサーバー起動時に `host="127.0.0.1"` を指定し、外部からのアクセスを遮断する。

### 9-3. 30日データ自動削除

バッチ実行時に以下のSQL相当の処理を実行する。

```sql
DELETE FROM articles
WHERE fetched_at < datetime('now', '-30 days');
```

---

## 10. テスト観点リスト（手順5でテスト設計書に展開）

| No. | 観点 | 確認内容 |
|---|---|---|
| T-01 | RSS取得 | Hoops RumorsのRSS正常取得 |
| T-02 | フェールオーバー | Hoops Rumors障害時にHoopsHypeへ切り替わるか |
| T-03 | 重複排除 | 同一URLの記事が重複保存されないか |
| T-04 | Spursフィルタ | `<category>`タグのキーワードマッチが正確か |
| T-05 | Claude API | 翻訳・要約・分類が正常に返るか |
| T-06 | カテゴリ分類 | 4分類の境界条件が正しく判定されるか |
| T-07 | ネタバレ防止 | `game`カテゴリの要約にスコアが含まれないか |
| T-08 | スコア表示 | BALLDONTLIEからのスコアデータが正しく表示されるか |
| T-09 | API上限管理 | 429エラー時に翻訳スキップ＋バナーが表示されるか |
| T-10 | 30日削除 | 30日超データが自動削除されるか |
| T-11 | フェールオーバー記録 | fetch_logsにフェールオーバー情報が記録されるか |
| T-12 | 設定変更 | ネタバレ防止・Spursフィルタの切替が即座に反映されるか |
| T-13 | パフォーマンス | ページ初期表示が1秒以内か（キャッシュ済みデータ表示） |
| T-14 | エンドツーエンド | RSS取得→翻訳→DB保存→画面表示の一連の流れが正常に動作するか |

---

## 11. フェーズ2（NFL拡張）への考慮

本フェーズ1では以下の拡張性を意識した設計とする。詳細はフェーズ2計画書で定義する。

| 設計上の考慮点 | 内容 |
|---|---|
| スポーツ種別の抽象化 | `config.py` にスポーツ種別（`NBA` / `NFL`）の定数を定義し、RSS URL・BALLDONTLIEエンドポイントを種別ごとに切り替えられる構造にする |
| BALLDONTLIEのNFL対応 | BALLDONTLIEはNFLに対応済みのため、フェーズ2でScore Fetcherを拡張するのみで対応可能 |
| カテゴリ定義の拡張 | カテゴリ定義は `config.py` で管理し、NFLで追加が必要なカテゴリ（ドラフト等）を追加しやすい構造にする |

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v0.1 | 2026-05-10 | 初版作成 |
