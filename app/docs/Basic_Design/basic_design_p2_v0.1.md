# 基本設計書（フェーズ2）

- **バージョン**: v0.1
- **ステータス**: Draft
- **作成日**: 2026-06-07
- **対象**: NBAニュース翻訳アプリ 改修（フェーズ2）
- **参照**:
  - 要件定義書 フェーズ2 v0.12（`requirements_p2_v0.12.md`）※Fix済み
  - リスク調査書 フェーズ2 v0.9（`risk_report_p2_v0.9.md`）※Fix済み
  - 基本設計書 フェーズ1 v0.4（`basic_design_v0.4.md`）※差分ベース

---

## 設計自己チェックリスト（レビュー提言2）

レビュー依頼前に以下を確認すること。

| # | 確認内容 | 状態 |
|---|---|---|
| 1 | フェーズ1基本設計書との差分が明示されているか | ⬜ |
| 2 | 数値・閾値に根拠が記述されているか（レビュー提言10） | ⬜ |
| 3 | DBスキーマの冗長カラムがないか | ⬜ |
| 4 | フェーズ1との断絶（インフラ変更）が独立セクションで明示されているか | ⬜ |
| 5 | C-04スコープアウト・C-05速報ニュースなしが設計に反映されているか | ⬜ |
| 6 | has_score=trueのフラグ制御ロジックが全コンポーネントで一貫しているか | ⬜ |

---

## 1. システム構成

### 1-1. フェーズ1からの構成変更概要

| 区分 | フェーズ1 | フェーズ2 | 変更内容 |
|---|---|---|---|
| 公開方式 | ローカル（localhost） | **外部公開（Render）** | **アーキテクチャ変更・致命-2対応** |
| 認証 | なし | **JWT認証（FastAPI）** | 新規追加 |
| カテゴリ数 | 4分類 | **5分類**（C-04スコープアウトのため） | Claude APIプロンプト変更 |
| Score Fetcher | 試合スコア取得 | **試合日程・スコア取得（C-05用）** | 機能拡張 |
| 重複排除 | URLのUNIQUE制約のみ | **タイトル類似度（Levenshtein）+is_duplicateフラグ** | 新規追加 |
| ネタバレ制御 | has_scoreフラグ（フェーズ1継承） | **has_scoreフラグ（継承・コラム含む全カテゴリに適用）** | 適用範囲拡大 |
| F-12外部リンク | なし | **NBA公式順位リンク（ヘッダー）** | 新規追加 |

### 1-2. 構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                          外部サービス                            │
│  Hoops Rumors RSS   Hoops Wire RSS   The Cold Wire NBA RSS       │
│  （主軸）           （FO1）          （FO2）                      │
│                                                                   │
│  BALLDONTLIE API（gamesエンドポイント）                           │
│  （C-05：試合日程・結果・スコア）                                 │
│                                                                   │
│  Claude API（翻訳・要約・カテゴリ分類・has_score判定）            │
│  NBA公式順位 https://www.nba.com/standings（F-12リンク先）        │
└────────────────────────┬────────────────────────────────────────┘
                          │ HTTPS
┌────────────────────────▼────────────────────────────────────────┐
│                  Render（Starterプラン・$7/月）                   │
│                  バックエンド（Python / FastAPI）                  │
│                                                                   │
│  ┌────────────┐  ┌───────────────┐  ┌──────────────────────┐    │
│  │ Scheduler  │  │  API Server   │  │   Claude Client      │    │
│  │(APScheduler│  │  (FastAPI)    │  │ (翻訳・要約・分類    │    │
│  │+ JWT Auth) │  │  +JWT検証     │  │  has_score判定)      │    │
│  └─────┬──────┘  └──────┬────────┘  └──────────────────────┘    │
│        │                │                                         │
│  ┌─────▼────────────────▼──────────────────────────────────┐    │
│  │                    SQLite DB                              │    │
│  │  articles / fetch_logs / app_settings / users            │    │
│  └──────────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────────┘
                          │ HTTPS（外部公開・JWT認証）
┌────────────────────────▼────────────────────────────────────────┐
│               フロントエンド（React SPA）                         │
│  カテゴリタブ / フィルタ / ネタバレ防止 / F-12外部リンク          │
│  スマホブラウザ対応                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 1-3. コンポーネント一覧（フェーズ2）

| コンポーネント | 役割 | 変更区分 |
|---|---|---|
| Scheduler | 前回取得から4時間経過を検知しバッチ処理を起動 | 変更なし |
| RSS Fetcher | フェールオーバー構成でRSSを取得 | 変更なし |
| Score Fetcher | BALLDONTLIEからC-05用試合日程・スコアを取得 | **機能拡張** |
| Claude Client | 翻訳・要約・カテゴリ分類・has_score判定（5分類対応） | **プロンプト変更** |
| Dedup Processor | タイトル類似度（Levenshtein）で重複判定・is_duplicateフラグ付与 | **新規追加** |
| API Server | REST API提供・JWT認証ミドルウェア | **認証追加** |
| Auth Module | JWT発行・検証・ユーザー管理 | **新規追加** |
| SQLite DB | 記事・取得ログ・アプリ設定・ユーザー情報を永続化 | **スキーマ変更** |
| Frontend | カテゴリタブ・フィルタ・ネタバレ防止UI・F-12外部リンク | **UI変更** |

---

## 2. インフラ変更（フェーズ1との断絶・致命-2対応）

> **注記：** 本セクションはフェーズ1の「ローカル限定」アーキテクチャからの変更を独立して記述する。他の機能改修（カテゴリ再編・認証等）とは独立したリスクとして扱う。

### 2-1. ホスティング

| 項目 | フェーズ1 | フェーズ2 |
|---|---|---|
| ホスト | localhost:8000 | **Render Starterプラン（$7/月）** |
| アクセス方法 | ローカルブラウザのみ | **HTTPS・外部公開** |
| FastAPI起動 | `host="127.0.0.1"` | **`host="0.0.0.0"`** |
| SSL | なし | **Render自動プロビジョニング** |
| スリープ | — | **なし（Starterプラン）** |

### 2-2. JWT認証

| 項目 | 内容 | 根拠 |
|---|---|---|
| ライブラリ | `python-jose`・`passlib` | FastAPI公式推奨（risk_report_p2_v0.9 §3-4） |
| トークン有効期限 | 30日 | 家族利用のため長め設定（requirements_p2_v0.12 §4 F-10） |
| パスワード管理 | 環境変数（`.env`） | APIキーと同様の管理方針 |
| 適用エンドポイント | `/api/news`・`/api/status`・`/api/settings` | 全APIエンドポイントに適用 |
| 非適用エンドポイント | `POST /api/auth/login` | ログインエンドポイントは認証不要 |

### 2-3. 環境変数の追加（フェーズ2）

```
# フェーズ2追加分
SECRET_KEY=（JWT署名キー・openssl rand -hex 32で生成）
USER_PASSWORD=（家族共有パスワード）
BALLDONTLIE_API_KEY=（フェーズ1から継続）
```

---

## 3. データフロー（変更箇所のみ記述）

フェーズ1のデータフロー（basic_design_v0.4.md §3）を基本とし、以下の変更点を追記する。

### 3-1. バッチ処理フロー（変更箇所）

```
[RSS Fetcher]（変更なし）
    ▼
[重複チェック①：URL一致チェック（既存）]
    │ articles.linkが同一 → スキップ（変更なし）
    ▼
【新規】[重複チェック②：タイトル類似度チェック（Dedup Processor）]
    │ 直近7日の記事タイトルとLevenshtein距離を計算
    │ 類似度80%以上 → is_duplicate=True でDB保存（非表示・修正可能）
    │ 類似度80%未満 → 処理継続
    ▼
[Spursフィルタ]（変更なし）
    ▼
[Claude Client: 翻訳・要約・分類]
    │ 出力（JSON）:
    │   - title_ja      : 翻訳済み見出し
    │   - summary_ja    : 日本語要約（800〜1200字）← フェーズ1は300〜500字
    │   - category      : トレード/FA / ドラフト / 試合日程 / けが人 / コラム
    │                     ← フェーズ1は4分類。フェーズ2は5分類（C-04スコープアウト）
    │   - has_score     : スコア・試合結果を含むか（Boolean）← 変更なし
    ▼
[Score Fetcher: BALLDONTLIE games]（変更なし・C-05表示用にも流用）
    ▼
[DB保存: articles テーブル]
    │ is_duplicate フラグを含めて保存 ← 新規カラム
    ▼
【新規】[C-05バッチ: 試合日程取得]
    │ BALLDONTLIE /v1/games?start_date=今日&end_date=今日+7日
    │ 取得した試合日程データを game_schedule テーブルに保存
    │ status=Final または In Progress → has_score=True（ぼかし表示）
    │ status=Scheduled → has_score=False（スコアなし・日程表示のみ）
```

### 3-2. APIレスポンスフロー（変更箇所）

```
【新規】GET /api/auth/login
    │ ユーザー名・パスワードを検証
    │ 正しければJWTトークン（有効期限30日）を返す
    ▼

GET /api/news（JWT認証必須）
    │ is_duplicate=False の記事のみ返す ← 変更
    │ カテゴリフィルタ（5分類対応） ← 変更
    │ has_score=True の記事はscore_data付き ← 変更なし

【新規】GET /api/schedule（JWT認証必須）
    │ game_schedule テーブルから試合日程を返す
    │ C-05タブ用
```

---

## 4. DBスキーマ（変更箇所のみ）

フェーズ1のDBスキーマ（basic_design_v0.4.md §4）を基本とし、以下の変更点を追記する。

### 4-1. articles テーブル（カラム追加）

| カラム名 | 型 | 変更区分 | 内容 |
|---|---|---|---|
| id | INTEGER PK | 変更なし | — |
| title | TEXT | 変更なし | — |
| title_ja | TEXT | 変更なし | — |
| summary_ja | TEXT | 変更なし | 800〜1200字（フェーズ1は300〜500字） |
| category | TEXT | **変更** | 5分類対応（trade_fa / draft / game / injury / column） |
| has_score | BOOLEAN | 変更なし | — |
| is_spurs | BOOLEAN | 変更なし | — |
| **is_duplicate** | **BOOLEAN** | **新規追加** | Levenshtein距離80%以上で重複と判定した場合True |
| link | TEXT UNIQUE | 変更なし | — |
| score_data | JSON | 変更なし | — |
| pub_date | DATETIME | 変更なし | — |
| fetched_at | DATETIME | 変更なし | — |

> **注記（冗長カラム排除）：** `source_url` カラムはフェーズ1で `link` と同値のため存在しない。フェーズ2でも追加しない。

### 4-2. game_schedule テーブル（新規追加）

C-05（試合日程）タブ用にBALLDONTLIEから取得した試合データを格納する。

| カラム名 | 型 | 内容 |
|---|---|---|
| id | INTEGER PK | — |
| game_id | TEXT UNIQUE | BALLDONTLIEのゲームID |
| game_date | DATE | 試合日（YYYY-MM-DD） |
| status | TEXT | Scheduled / In Progress / Final |
| home_team | TEXT | ホームチーム略称 |
| visitor_team | TEXT | アウェイチーム略称 |
| home_score | INTEGER NULL | ホームチームスコア（未終了はNULL） |
| visitor_score | INTEGER NULL | アウェイチームスコア（未終了はNULL） |
| has_score | BOOLEAN | Final or In Progress → True（ぼかし表示対象） |
| fetched_at | DATETIME | 取得日時 |

### 4-3. users テーブル（新規追加）

JWT認証用のユーザー情報を格納する。

| カラム名 | 型 | 内容 |
|---|---|---|
| id | INTEGER PK | — |
| username | TEXT UNIQUE | ユーザー名 |
| hashed_password | TEXT | bcryptハッシュ化済みパスワード |
| created_at | DATETIME | 作成日時 |

---

## 5. カテゴリ分類プロンプト設計（変更箇所）

### 5-1. フェーズ1との差分

| 項目 | フェーズ1 | フェーズ2 |
|---|---|---|
| 分類数 | 4分類（trade/contract/game/column） | **5分類（trade_fa/draft/game/injury/column）** |
| 要約文字数 | 300〜500字 | **800〜1200字** |
| カテゴリ定義 | トレード/契約/試合結果/コラム | **トレード/FA/ドラフト/試合日程/けが人/コラム** |

### 5-2. プロンプト設計方針

```
システムプロンプト（変更箇所のみ）:

カテゴリ分類は以下の5分類で行ってください：
- trade_fa  : トレード・移籍・FA・契約情報
- draft     : ドラフト候補・指名・撤退情報
- game      : 試合速報・スコア・試合結果（スコアが主要情報）
- injury    : インジャリーレポート・欠場・復帰情報
- column    : 試合分析・選手評価・戦術・インタビュー・その他
              ※ スコアが引用で含まれる場合もcolumnに分類

要約はsummary_jaフィールドに800〜1200字で生成してください。

has_scoreはスコア・試合結果が本文の主要情報として含まれる場合にtrueを設定してください。
タブを問わず、スコアが記事の主要情報である場合はhas_score=trueとしてください。
```

### 5-3. カテゴリ境界ケースのプロンプト指示

| ケース | 分類 | プロンプトへの指示 |
|---|---|---|
| インジャリーレポート | injury | 「欠場・復帰・負傷情報はinjuryに分類」と明示 |
| FAコラム（分析記事） | trade_fa | 「FA動向の分析記事はtrade_faに分類」と明示 |
| 試合分析（スコア引用） | column | 「スコアが引用として含まれる場合はcolumnに分類」と明示 |

---

## 6. フロントエンド設計（変更箇所）

### 6-1. 画面構成の変更

| 変更内容 | 詳細 |
|---|---|
| ログイン画面（新規） | JWT認証用。ユーザー名・パスワード入力→トークン取得 |
| カテゴリタブ | 5タブ構成（すべて / トレード/FA / ドラフト / 試合日程 / けが人 / コラム） |
| F-12外部リンク | ヘッダーに「📊 現在の順位」→ `https://www.nba.com/standings`（target="_blank"） |
| C-05試合日程タブ | APIデータの試合日程・スコアを専用コンポーネントで表示 |
| ネタバレ防止 | has_score=trueの記事・試合データ全てにSpoilerOverlayを適用 |
| レスポンシブ | スマホブラウザ対応（Tailwind CSSのブレークポイント活用） |

### 6-2. 新規コンポーネント

| コンポーネント | 内容 |
|---|---|
| `LoginForm.jsx` | ログイン画面（ユーザー名・パスワード入力） |
| `GameSchedule.jsx` | C-05タブ用の試合日程・スコア表示 |

### 6-3. 変更コンポーネント

| コンポーネント | 変更内容 |
|---|---|
| `CategoryTabs.jsx` | 5タブ対応・F-12リンクボタン追加 |
| `SpoilerOverlay.jsx` | has_score=trueの全カテゴリに適用（コラム含む） |
| `App.jsx` | JWT認証状態管理・未認証時はLoginFormを表示 |

---

## 7. ディレクトリ構成（変更箇所）

フェーズ1の構成（basic_design_v0.4.md §2-2）に以下を追加・変更する。

```
backend/
├── auth/                        ← 新規追加
│   ├── jwt.py                   # JWT発行・検証
│   └── users.py                 # ユーザー管理
├── processor/
│   ├── claude_client.py         # 5分類対応・要約文字数変更
│   ├── filter.py                # 変更なし
│   └── dedup.py                 ← 新規追加（Levenshtein重複排除）
├── fetcher/
│   ├── rss.py                   # 変更なし
│   └── score.py                 # C-05試合日程取得機能を追加
├── db/
│   └── models.py                # is_duplicate・game_schedule・usersを追加
└── api/
    └── routes.py                # 認証エンドポイント・/api/scheduleを追加

frontend/src/components/
├── LoginForm.jsx                 ← 新規追加
├── GameSchedule.jsx              ← 新規追加（C-05タブ用）
├── CategoryTabs.jsx              # 5タブ・F-12リンク対応
├── SpoilerOverlay.jsx            # 全カテゴリhas_score適用
└── App.jsx                       # JWT認証状態管理
```

---

## 8. 残課題（詳細設計で確定）

| # | 課題 | 詳細設計での確定内容 |
|---|---|---|
| D-01 | Levenshtein距離の比較対象 | title_ja（日本語訳後）か title（原文）か。翻訳前の方が安定する可能性あり |
| D-02 | C-05試合日程の取得頻度 | バッチと同周期（4時間）か、専用スケジュールを設けるか |
| D-03 | `status=In Progress`の更新頻度 | リアルタイム更新は不要と判断しているが詳細設計で確定 |
| D-04 | game_scheduleの保持期間 | articlesと同様30日か、別途定義するか |
| D-05 | Renderのデプロイ方式 | GitHubリポジトリ連携か、手動デプロイか |

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v0.1 | 2026-06-07 | 初版作成。フェーズ1基本設計書（v0.4）を差分ベースとしてフェーズ2の変更点のみを記述。設計自己チェックリスト・インフラ変更独立セクション・DBスキーマ差分・カテゴリプロンプト設計・フロントエンド変更点・ディレクトリ構成変更・残課題を記載 |
