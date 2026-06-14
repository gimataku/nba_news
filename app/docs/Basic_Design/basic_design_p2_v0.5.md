# 基本設計書（フェーズ2）

- **バージョン**: v0.5
- **ステータス**: 完了
- **作成日**: 2026-06-07
- **更新日**: 2026-06-14
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
| 1 | フェーズ1基本設計書との差分が明示されているか | ✅ |
| 2 | 数値・閾値に根拠が記述されているか（レビュー提言10） | ✅ |
| 3 | DBスキーマの冗長カラムがないか | ✅ |
| 4 | フェーズ1との断絶（インフラ変更）が独立セクションで明示されているか | ✅ |
| 5 | C-04スコープアウト・C-05速報ニュースなしが設計に反映されているか | ✅ |
| 6 | has_score=trueのフラグ制御ロジックが全コンポーネントで一貫しているか | ✅ |

---

## 1. システム構成

### 1-1. フェーズ1からの構成変更概要

| 区分 | フェーズ1 | フェーズ2 | 変更内容 |
|---|---|---|---|
| 公開方式 | ローカル（localhost） | **外部公開（Render）** | **アーキテクチャ変更・致命-2対応** |
| 認証 | なし | **JWT認証（FastAPI）** | 新規追加 |
| Claude API分類カテゴリ | 4分類（trade/contract/game/column） | **4分類（trade_fa/draft/injury/column）** | gameカテゴリ廃止・draft/injury新設 |
| 表示タブ | 4タブ | **6タブ（すべて含む）** | C-04スコープアウト・C-05はAPIデータ専用タブ |
| Score Fetcher | 試合スコア取得 | **試合日程・スコア取得（C-05用）** | **機能拡張**（score.pyにC-05バッチ用関数を追加） |
| 重複排除 | URLのUNIQUE制約のみ | **タイトル類似度（Levenshtein・原文）+is_duplicateフラグ** | 新規追加 |
| ネタバレ制御 | has_scoreフラグ（フェーズ1継承） | **has_scoreフラグ（継承・コラム含む全カテゴリに適用）** | 適用範囲拡大 |
| F-12外部リンク | なし | **NBA公式順位リンク（ヘッダー）** | 新規追加 |
| DB永続化 | ローカルファイル（問題なし） | **Render Persistent Disk（$0.25/GB/月）** | エフェメラルFS対策（RED-01対応） |

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
│           + Persistent Disk（1GB・$0.25/月）                     │
│                  バックエンド（Python / FastAPI）                  │
│                                                                   │
│  ┌────────────┐  ┌───────────────┐  ┌──────────────────────┐    │
│  │ Scheduler  │  │  API Server   │  │   Claude Client      │    │
│  │(APScheduler│  │  (FastAPI)    │  │ (翻訳・要約・分類    │    │
│  │+ JWT Auth) │  │  +JWT検証     │  │  has_score判定)      │    │
│  └─────┬──────┘  └──────┬────────┘  └──────────────────────┘    │
│        │                │                                         │
│  ┌─────▼────────────────▼──────────────────────────────────┐    │
│  │         SQLite DB（/data/nba_news.db）                    │    │
│  │         Persistent Diskにマウント・デプロイ後も保持       │    │
│  │  articles / fetch_logs / app_settings / users / game_schedule │
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
| Score Fetcher | BALLDONTLIEからC-05用試合日程・スコアを取得 | **機能拡張**（記事スコア取得ロジック自体は変更なし。score.pyにC-05バッチ用の試合日程取得関数を追加） |
| Claude Client | 翻訳・要約・カテゴリ分類・has_score判定（4分類対応） | **プロンプト変更** |
| Dedup Processor | タイトル類似度（Levenshtein・原文）で重複判定・is_duplicateフラグ付与 | **新規追加** |
| API Server | REST API提供・JWT認証ミドルウェア | **認証追加** |
| Auth Module | JWT発行・検証・ユーザー管理 | **新規追加** |
| SQLite DB | 記事・取得ログ・アプリ設定・ユーザー情報を永続化（Persistent Disk） | **スキーマ変更・永続化対応** |
| Frontend | カテゴリタブ・フィルタ・ネタバレ防止UI・F-12外部リンク | **UI変更** |

---

## 2. インフラ変更（フェーズ1との断絶・致命-2対応）

> **注記：** 本セクションはフェーズ1の「ローカル限定」アーキテクチャからの変更を独立して記述する。他の機能改修（カテゴリ再編・認証等）とは独立したリスクとして扱う。

### 2-1. ホスティングとDB永続化（RED-01対応）

| 項目 | フェーズ1 | フェーズ2 |
|---|---|---|
| ホスト | localhost:8000 | **Render Starterプラン（$7/月）** |
| アクセス方法 | ローカルブラウザのみ | **HTTPS・外部公開** |
| FastAPI起動 | `host="127.0.0.1"` | **`host="0.0.0.0"`** |
| SSL | なし | **Render自動プロビジョニング** |
| スリープ | — | **なし（Starterプラン）** |
| **DB永続化** | ローカルファイル（問題なし） | **Render Persistent Disk（$0.25/GB/月・1GB）を追加** |
| **SQLiteマウントパス** | — | **`/data/nba_news.db`（Persistent Diskにマウント）** |
| **デプロイ方式** | — | **GitHubリポジトリ連携（push → 自動デプロイ）** |

> **設計根拠（RED-01対応）：** RenderのStarter planはエフェメラルファイルシステムを採用しており、デプロイ・サービス再起動のたびにコンテナがリセットされる。SQLiteファイルが揮発するとarticles・users・app_settingsのデータがすべて失われる。対処として**案A（Render Persistent Disk）を採用**し、`/data/nba_news.db` をPersistent Diskにマウントすることでデプロイ後もデータを保持する。
>
> **デプロイ方式確定（D-05）：** GitHubリポジトリをRenderサービスに連携し、mainブランチへのpushで自動デプロイを行う。詳細手順（ブランチ戦略・環境変数設定手順）は詳細設計書で確定する。

### 2-2. JWT認証

| 項目 | 内容 | 根拠 |
|---|---|---|
| ライブラリ | `python-jose`・`passlib` | FastAPI公式推奨（risk_report_p2_v0.9 §3-4） |
| トークン有効期限 | 30日 | 家族利用のため長め設定（requirements_p2_v0.12 §4 F-10） |
| パスワード管理 | 環境変数 `USER_PASSWORD`（平文） → 起動時initスクリプトがbcryptハッシュ化してusersテーブルに投入 | APIキーと同様の管理方針。二重管理ではなく「環境変数 → usersテーブルへの初期投入フロー」（YEL-03対応） |
| 適用エンドポイント | `/api/news`・`/api/status`・`/api/settings`・**`/api/schedule`** | 全APIエンドポイントに適用（YEL-04対応） |
| 非適用エンドポイント | `POST /api/auth/login` | ログインエンドポイントは認証不要 |

> **初回ユーザー作成フロー（YEL-03対応）：**
> 1. `.env` に `USERNAME=admin`・`USER_PASSWORD=（平文パスワード）` を設定
> 2. アプリ起動時（`main.py` の startup イベント）にinitスクリプトが `usersテーブル` の存在を確認
> 3. usersテーブルが空の場合のみ、`USER_PASSWORD` をbcryptでハッシュ化して1件登録
> 4. usersテーブルに既にレコードが存在する場合はスキップ（冪等性を確保）

### 2-3. 環境変数の追加（フェーズ2）

```
# フェーズ2追加分
SECRET_KEY=（JWT署名キー・openssl rand -hex 32で生成）
USERNAME=（ユーザー名・初期ユーザー名）
USER_PASSWORD=（家族共有パスワード・平文・起動時にhash化してDB投入）
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
    │ 直近7日の記事タイトル（原文・英語）とLevenshtein距離を計算
    │ 類似度80%以上 → is_duplicate=True でDB保存（非表示・修正可能）→ 以降の処理をスキップ
    │ 類似度80%未満 → 処理継続
    │
    │ ※ 比較対象はtitle（原文・英語）。翻訳前に実行することで
    │   翻訳コスト削減・フロー順序の整合性を確保（RED-03対応）
    │
    │ ※ 閾値80%の根拠：英語タイトルでの字句的類似度として
    │   誤検知（異なる記事を重複と誤判定）と見逃し（重複を通過）の
    │   バランスから選定（要件定義書F-11 方針Bに基づく）（GRN-02対応）
    ▼
[Spursフィルタ]（変更なし）
    ▼
[Claude Client: 翻訳・要約・分類]
    │ 出力（JSON）:
    │   - title_ja      : 翻訳済み見出し
    │   - summary_ja    : 日本語要約（800〜1200字）← フェーズ1は300〜500字
    │   - category      : trade_fa / draft / injury / column（4分類）
    │                     ← フェーズ1は4分類（trade/contract/game/column）
    │                     ← フェーズ2はgame廃止・draft/injury新設（YEL-01対応）
    │   - has_score     : スコア・試合結果を含むか（Boolean）← 変更なし
    ▼
[Score Fetcher: BALLDONTLIE games]
    │ 機能拡張：記事スコア取得ロジック自体は変更なし。
    │ score.pyにC-05バッチ用の試合日程取得関数を追加（NEW-YEL-01対応）
    ▼
[DB保存: articles テーブル]
    │ is_duplicate フラグを含めて保存 ← 新規カラム
    ▼
【新規】[C-05バッチ: 試合日程取得]（RSSバッチと同周期・4時間ごと）
    │ BALLDONTLIE /v1/games?start_date=今日-1日&end_date=今日+7日
    │ ※ start_date=今日-1日の理由（NEW-YEL-02対応）：NBA試合は日本時間深夜〜早朝に
    │   開催されるため、翌日のバッチ実行時点で「昨日の試合」がFinal未反映になる
    │   ケースがある。1日前からの取得で取り漏れを防ぐ。
    │ 取得した試合データをgame_scheduleテーブルにUPSERT（INSERT OR REPLACE）で書き込む
    │ game_idをキーとして既存レコードのstatus・has_score・スコアを上書きすることで
    │ 試合進行（Scheduled → In Progress → Final）に追随する（NEW-YEL-01対応）
    │ status=Final または In Progress → has_score=True（ぼかし表示）
    │ status=Scheduled → has_score=False（スコアなし・日程表示のみ）
    │
    │ ※ In Progressをネタバレ防止対象とする理由（YEL-05対応）：
    │   試合進行中のためスコアが確定していないが、次回バッチ（4時間後）で
    │   Finalに更新されるまでの間もネタバレ防止対象とする。
    │   リアルタイム更新は行わない（D-03確定済み）。
    │
    │ ※ 取得頻度の確定（YEL-06対応 / D-02確定）：
    │   RSSバッチと同周期（4時間ごと）でC-05データを取得する。
    │   試合結果（Final）の反映が最大4時間遅れる可能性があるが、
    │   個人・家族利用の範囲では許容する。
```

### 3-2. APIレスポンスフロー（変更箇所）

```
【新規】POST /api/auth/login（RED-02対応・GETからPOSTに変更）
    │ Body: {"username": "...", "password": "..."}
    │ ユーザー名・パスワードを検証（usersテーブル照会）
    │ 正しければJWTトークン（有効期限30日）を返す
    │ ※ GETは不可（URLにパスワードが露出しRenderのアクセスログに残るリスク）
    ▼

GET /api/news（JWT認証必須）
    │ is_duplicate=False の記事のみ返す ← 変更
    │ カテゴリフィルタ（4分類対応） ← 変更
    │ has_score=True の記事はscore_data付き ← 変更なし

【新規】GET /api/schedule（JWT認証必須）
    │ game_schedule テーブルから試合日程を返す
    │ C-05タブ用（articles.category="game"は含まない）
```

---

## 4. DBスキーマ（変更箇所のみ）

フェーズ1のDBスキーマ（basic_design_v0.4.md §4）を基本とし、以下の変更点を追記する。

### 4-1. articles テーブル（カラム追加・変更）

| カラム名 | 型 | 変更区分 | 内容 |
|---|---|---|---|
| id | INTEGER PK | 変更なし | — |
| title | TEXT | 変更なし | — |
| title_ja | TEXT | 変更なし | — |
| summary_ja | TEXT | 変更なし | 800〜1200字（フェーズ1は300〜500字） |
| category | TEXT | **変更** | 4分類対応（trade_fa / draft / injury / column）。gameカテゴリは廃止（YEL-01対応） |
| has_score | BOOLEAN | 変更なし | — |
| is_spurs | BOOLEAN | 変更なし | — |
| **is_duplicate** | **BOOLEAN** | **新規追加** | Levenshtein距離80%以上で重複と判定した場合True |
| link | TEXT UNIQUE | 変更なし | — |
| score_data | JSON | 変更なし | — |
| pub_date | DATETIME | 変更なし | — |
| fetched_at | DATETIME | 変更なし | — |

> **注記（冗長カラム排除）：** `source_url` カラムはフェーズ1で `link` と同値のため存在しない。フェーズ2でも追加しない。
>
> **注記（GRN-03対応）：** articles.category に "game" は存在しない（廃止）。C-05（試合日程）タブは game_schedule テーブルのBALLDONTLIEデータのみを表示する。RSS記事で試合結果を扱うものは "column" に分類される。

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

> **更新方式（NEW-YEL-01対応）：** C-05バッチは取得した全試合データをUPSERT（INSERT OR REPLACE）でgame_scheduleテーブルに書き込む。game_idをUNIQUEキーとして既存レコードのstatus・has_score・スコアを上書きすることで、試合進行（Scheduled → In Progress → Final）に追随する。単純INSERTやINSERT OR IGNOREは既存レコードが更新されないため使用しない。

### 4-3. users テーブル（新規追加）

JWT認証用のユーザー情報を格納する。初回ユーザーはアプリ起動時のinitスクリプトにより自動投入される（§2-2参照）。

| カラム名 | 型 | 内容 |
|---|---|---|
| id | INTEGER PK | — |
| username | TEXT UNIQUE | ユーザー名（環境変数 `USERNAME` から初期投入） |
| hashed_password | TEXT | bcryptハッシュ化済みパスワード（環境変数 `USER_PASSWORD` をhash化） |
| created_at | DATETIME | 作成日時 |

### 4-4. app_settings テーブル（変更なし）

フェーズ2のF-05（has_score=trueフラグ単位制御への変更）に伴うapp_settingsテーブルのスキーマ変更はなし。フェーズ1の `spoiler_guard_enabled` キーは全体ON/OFFの単一フラグ（タブ単位設定ではない）であるため、F-05対応においてカラムの追加・削除は不要（NEW-GRN-01対応）。

---

## 5. カテゴリ分類プロンプト設計（変更箇所）

### 5-1. フェーズ1との差分

| 項目 | フェーズ1 | フェーズ2 |
|---|---|---|
| Claude API分類数 | 4分類（trade/contract/game/column） | **4分類（trade_fa/draft/injury/column）**（YEL-01対応） |
| 表示タブ数 | 4タブ | **6タブ（すべて含む）** |
| C-05試合日程 | — | **BALLDONTLIEデータ専用タブ（Claude分類対象外）** |
| 要約文字数 | 300〜500字 | **800〜1200字** |
| カテゴリ定義変更 | trade/contract → trade_fa に統合、game廃止、draft/injury新設 | — |

### 5-2. プロンプト設計方針

```
システムプロンプト（変更箇所のみ）:

カテゴリ分類は以下の4分類で行ってください：
- trade_fa  : トレード・移籍・FA・契約情報
- draft     : ドラフト候補・指名・撤退情報
- injury    : インジャリーレポート・欠場・復帰情報
- column    : 試合分析・試合速報・スコア記事・選手評価・戦術・インタビュー・その他
              ※ 試合結果・スコアが主要情報の記事もcolumnに分類（gameカテゴリなし）

要約はsummary_jaフィールドに800〜1200字で生成してください。

has_scoreはスコア・試合結果が本文の主要情報として含まれる場合にtrueを設定してください。
タブを問わず、スコアが記事の主要情報である場合はhas_score=trueとしてください。
```

### 5-3. カテゴリ境界ケースのプロンプト指示

| ケース | 分類 | プロンプトへの指示 |
|---|---|---|
| インジャリーレポート | injury | 「欠場・復帰・負傷情報はinjuryに分類」と明示 |
| FAコラム（分析記事） | trade_fa | 「FA動向の分析記事はtrade_faに分類」と明示 |
| 試合結果・スコア速報 | column | 「試合結果・スコアが主要情報の記事もcolumnに分類」と明示 |
| 試合分析（スコア引用） | column | 「スコアが引用として含まれる場合はcolumnに分類」と明示 |

---

## 6. フロントエンド設計（変更箇所）

### 6-1. 画面構成の変更

| 変更内容 | 詳細 |
|---|---|
| ログイン画面（新規） | JWT認証用。ユーザー名・パスワード入力→トークン取得 |
| カテゴリタブ | **6タブ構成**：すべて / トレード/FA / ドラフト / 試合日程 / けが人 / コラム（YEL-01対応） |
| F-12外部リンク | ヘッダーに「📊 現在の順位」→ `https://www.nba.com/standings`（target="_blank"） |
| C-05試合日程タブ | game_scheduleテーブルのAPIデータを専用コンポーネントで表示。articles（RSS記事）は含まない |
| ネタバレ防止 | has_score=trueの記事・試合データ全てにSpoilerOverlayを適用 |
| レスポンシブ | スマホブラウザ対応（Tailwind CSSのブレークポイント活用） |

**タブ定義：**

| タブ表示名 | データソース | Claude分類値 |
|---|---|---|
| すべて | articles（is_duplicate=False） | 全分類 |
| トレード/FA | articles | trade_fa |
| ドラフト | articles | draft |
| 試合日程 | game_schedule（BALLDONTLIEデータ） | C-05専用（Claude分類なし） |
| けが人 | articles | injury |
| コラム | articles | column |

### 6-2. 新規コンポーネント

| コンポーネント | 内容 |
|---|---|
| `LoginForm.jsx` | ログイン画面（ユーザー名・パスワード入力） |
| `GameSchedule.jsx` | C-05タブ用の試合日程・スコア表示 |

### 6-3. 変更コンポーネント

| コンポーネント | 変更内容 |
|---|---|
| `CategoryTabs.jsx` | 6タブ対応・F-12リンクボタン追加 |
| `SpoilerOverlay.jsx` | has_score=trueの全カテゴリに適用（コラム含む）。**F-05b対応：ネタバレ防止OFFにした後ONに戻せるよう修正**（YEL-02対応） |
| `App.jsx` | JWT認証状態管理・未認証時はLoginFormを表示 |

---

## 7. ディレクトリ構成（変更箇所）

フェーズ1の構成（basic_design_v0.4.md §2-2）に以下を追加・変更する。

```
backend/
├── auth/                        ← 新規追加
│   ├── jwt.py                   # JWT発行・検証
│   └── users.py                 # ユーザー管理・initスクリプト
├── processor/
│   ├── claude_client.py         # 4分類対応・要約文字数変更
│   ├── filter.py                # 変更なし
│   └── dedup.py                 ← 新規追加（Levenshtein重複排除）
├── fetcher/
│   ├── rss.py                   # 変更なし
│   └── score.py                 # C-05試合日程取得機能を追加（機能拡張）
├── db/
│   └── models.py                # is_duplicate・game_schedule・usersを追加
└── api/
    └── routes.py                # 認証エンドポイント・/api/scheduleを追加

frontend/src/components/
├── LoginForm.jsx                 ← 新規追加
├── GameSchedule.jsx              ← 新規追加（C-05タブ用）
├── CategoryTabs.jsx              # 6タブ・F-12リンク対応
├── SpoilerOverlay.jsx            # 全カテゴリhas_score適用・F-05b ON戻し修正
└── App.jsx                       # JWT認証状態管理
```

---

## 8. 残課題（詳細設計で確定）

| # | 課題 | 詳細設計での確定内容 |
|---|---|---|
| D-04 | game_scheduleの保持期間 | articlesと同様30日か、別途定義するか |
| D-06 | JWTトークンのフロントエンド保存先 | localStorage / sessionStorage / メモリ（Reactステート）のいずれかを詳細設計で確定。App.jsxの実装方針に直結（NEW-GRN-02対応） |

> **確定済み（各バージョンで閉じた残課題）：**
> - D-01 Levenshtein比較対象 → **title（原文・英語）に確定**（v0.2・RED-03対応）
> - D-02 C-05試合日程の取得頻度 → **4時間バッチと同周期に確定**（v0.2・YEL-06対応）
> - D-03 `status=In Progress`の更新頻度 → **リアルタイム更新は行わない（不要）に確定**（v0.4・NEW-GRN-01対応）
> - D-05 Renderのデプロイ方式 → **GitHubリポジトリ連携（自動デプロイ）に確定**（v0.2・RED-01対応）

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v0.1 | 2026-06-07 | 初版作成。フェーズ1基本設計書（v0.4）を差分ベースとしてフェーズ2の変更点のみを記述。設計自己チェックリスト・インフラ変更独立セクション・DBスキーマ差分・カテゴリプロンプト設計・フロントエンド変更点・ディレクトリ構成変更・残課題を記載 |
| v0.2 | 2026-06-14 | レビュー指摘（🔴3件・🟡6件・🟢3件）を全12件反映。①Render Persistent Disk追加・SQLiteマウントパス確定・デプロイ方式確定（RED-01）、②POST /api/auth/login に変更（RED-02）、③Levenshtein比較対象をtitle原文に確定・D-01クローズ（RED-03）、④Claude API分類を4分類（trade_fa/draft/injury/column）に統一・game廃止・タブ数を6タブと明記（YEL-01）、⑤SpoilerOverlay.jsxにF-05b（ネタバレ防止ON戻し修正）を追記（YEL-02）、⑥initスクリプトによる初回ユーザー作成フローを§2-2・§4-3に追記（YEL-03）、⑦/api/scheduleをJWT適用エンドポイントに追加（YEL-04）、⑧In Progress→has_score=Trueの根拠注記を追加（YEL-05）、⑨C-05取得頻度を4時間バッチと同周期に確定・D-02クローズ（YEL-06）、⑩自己チェックリストを全件✅に更新（GRN-01）、⑪Levenshtein 80%閾値の根拠を追記（GRN-02）、⑫gameカテゴリ廃止によりarticles.category="game"とC-05タブの関係を解消・注記追加（GRN-03） |
| v0.3 | 2026-06-14 | レビュー指摘（🟡2件・🟢2件）を全4件反映。①game_scheduleテーブルのUPSERT（INSERT OR REPLACE）方式を§3-1・§4-2に追記（NEW-YEL-01）、②C-05バッチのstart_date=今日-1日の根拠（日本時間深夜開催の試合取り漏れ防止）を§3-1に追記（NEW-YEL-02）、③変更履歴⑤のタイポ修正（SpoilerOverlay.jsc→.jsx）（NEW-GRN-01）、④JWTトークンのフロントエンド保存先をD-06として§8残課題に追加（NEW-GRN-02） |
| v0.4 | 2026-06-14 | レビュー指摘（🟡1件・🟢2件）を全3件反映。①構成図（§1-2）SQLite DB行にgame_scheduleを追記（NEW-YEL-01）、②D-03（In Progress更新頻度）を確定済みリストに移動・リアルタイム更新不要で確定・§3-1注記も更新（NEW-GRN-01）、③§3-1 Dedup Processorフローのis_duplicate=True行に「以降の処理をスキップ」を追記（NEW-GRN-02） |
| v0.5 | 2026-06-14 | レビュー指摘（🟡1件・🟢1件）を全2件反映。①Score Fetcherの変更区分を§1-1・§1-3・§3-1・§7で「機能拡張（記事スコア取得ロジック自体は変更なし・score.pyにC-05バッチ用試合日程取得関数を追加）」に統一（NEW-YEL-01）、②§4-4としてapp_settingsテーブルはF-05対応においてスキーマ変更なしと確認・注記を追加（NEW-GRN-01） |
