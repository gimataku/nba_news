# NBA News JP

海外NBAニュースのRSSを定期取得し、Claude APIで日本語に要約・カテゴリ分類してブラウザで閲覧できる個人用ローカルアプリです。

---

## 主な機能

- **RSS自動取得**：Hoops Rumors / Hoops Wire / The Cold Wire NBA を4時間ごとに取得（フェールオーバー対応）
- **AI翻訳・要約**：Claude API（claude-haiku-4-5-20251001）で英語記事を日本語タイトル・800〜1200字要約に変換
- **カテゴリ分類**：`trade_fa`（トレード/FA）/ `draft`（ドラフト）/ `injury`（けが人）/ `column`（コラム）の4分類に自動分類。重複記事（`is_duplicate=True`）は全タブで非表示
- **チームフィルタ**：San Antonio Spurs 関連記事のみを絞り込み表示
- **ネタバレ防止**：試合スコア・勝敗を含む記事（`has_score=True`）を折りたたみ表示（全カテゴリ対象）
- **試合日程取得**：BALLDONTLIE API から試合日程・スコアを取得し専用タブで表示
- **JWT認証**：ログイン必須（ユーザー名・パスワード）。トークンはブラウザのメモリにのみ保持（ローカルストレージ不使用）
- **データ自動削除**：30日経過した記事を自動削除

---

## 技術スタック

| レイヤー | 使用技術 |
|---|---|
| バックエンド | Python 3.11 / FastAPI / SQLite3 / APScheduler |
| フロントエンド | React 18 / Vite / Tailwind CSS |
| 外部API | Claude API / BALLDONTLIE API / RSS |

---

## ディレクトリ構成

```
NBA_news/
├── app
│   ├── backend/
│   │   ├── main.py            # FastAPI エントリーポイント
│   │   ├──scheduler.py       # バッチ処理・APScheduler 設定
│   │   ├──config.py          # 環境変数・定数
│   │   ├──fetcher/
│   │   │   ├── rss.py         # RSS取得
│   │   │   └── score.py       # BALLDONTLIE スコア取得
│   │   ├── processor/
│   │   │   ├── claude_client.py  # Claude API 翻訳・分類
│   │   │   └── filter.py         # Spurs 関連フィルタ
│   │   ├── db/
│   │   │   ├── models.py      # テーブル定義・DB初期化
│   │   │   └── crud.py        # CRUD 操作
│   │   ├── api/
│   │   |   ├── routes.py      # FastAPI ルーティング
│   ├── frontend/
│   │   └── src/
│   │       ├── App.jsx
│   │       └── components/    # FilterBar / CategoryTabs / NewsCard 等
│   ├── logs/
│   │   └── nba_news.log
│   ├── docs/                  # ドキュメント類
│   │   └── Basic_Design/      # 基本設計書
│   │   └── Detail_Design/     # 詳細設計書
│   │   └── Project_Plan/      # プロジェクト計画書
│   │   └── Requirement/       # 要件定義書
│   │   └── Risk_Report/       # リスク調査書
│   │   └── Test_Design/       # テスト設計書
│   │   └── Trial/             # トライアル運用関連
├── .env.example
├── setup.md               # 環境構築手順
├── README.md
└── CLAUDE.md
```

---

## セットアップ

詳細な手順は [setup.md](./setup.md) を参照してください。以下は概要です。

### 1. 前提条件

- Python 3.11 以上
- Node.js 18 以上

### 2. .env の準備

```bash
cp .env.example .env
# .env を開き以下の変数を記入
# ANTHROPIC_API_KEY / BALLDONTLIE_API_KEY / SECRET_KEY（任意の長い文字列）/ USERNAME / USER_PASSWORD
```

### 3. バックエンド依存パッケージのインストール

```bash
pip install fastapi uvicorn[standard] sqlalchemy apscheduler feedparser requests anthropic python-dotenv pydantic python-Levenshtein python-jose[cryptography] passlib[bcrypt] "bcrypt<4.0.0"
```
または requirements.txt を使う場合：
```bash
pip install -r backend/requirements.txt
```

### 4. フロントエンド依存パッケージのインストール

```bash
cd frontend && npm install
```

---

## 起動方法

バックエンドとフロントエンドをそれぞれ別ターミナルで起動します。

```bash
# バックエンド（ポート 8000）
cd backend && python main.py

# フロントエンド（ポート 5173）
cd frontend && npm run dev
```

ブラウザで `http://localhost:5173` を開くと画面が表示されます。

起動後、初回バッチが自動実行されRSSが取得されます。その後は4時間ごとに自動更新されます。

---

## API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/api/auth/login` | ログイン（ユーザー名・パスワード → JWTトークン発行） |
| GET | `/api/news` | 記事一覧取得（要認証。category / spurs_only / limit / offset でフィルタ可） |
| GET | `/api/schedule` | 試合日程一覧取得（要認証） |
| GET | `/api/status` | 最終取得日時・使用ソース・API制限状態（要認証） |
| GET | `/api/settings` | 設定値取得（要認証） |

---

## 環境変数

`.env.example` を参考に `.env` を作成してください。

| 変数名 | 説明 | 取得先 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API キー | https://console.anthropic.com/ |
| `BALLDONTLIE_API_KEY` | BALLDONTLIE API キー | https://app.balldontlie.io/ |
| `SECRET_KEY` | JWT署名用シークレット（任意の長い文字列） | 自分で生成（例：`openssl rand -hex 32`） |
| `USERNAME` | ログインユーザー名 | 自分で設定 |
| `USER_PASSWORD` | ログインパスワード | 自分で設定 |

---

## ログ

```
logs/nba_news.log
```

バッチ実行・RSS取得・Claude API 呼び出し・エラーが記録されます。

---

## ライセンス

個人利用のみを目的としたプロジェクトです。
