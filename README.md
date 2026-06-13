# NBA News JP

海外NBAニュースのRSSを定期取得し、Claude APIで日本語に要約・カテゴリ分類してブラウザで閲覧できる個人用ローカルアプリです。

---

## 主な機能

- **RSS自動取得**：Hoops Rumors / Hoops Wire / The Cold Wire NBA を4時間ごとに取得（フェールオーバー対応）
- **AI翻訳・要約**：Claude API（claude-haiku）で英語記事を日本語タイトル・300〜500字要約に変換
- **カテゴリ分類**：`trade` / `contract` / `game` / `column` の4カテゴリに自動分類
- **チームフィルタ**：San Antonio Spurs 関連記事のみを絞り込み表示
- **ネタバレ防止**：試合結果（スコア）を含む記事を折りたたみ表示
- **スコア取得**：game カテゴリの記事に BALLDONTLIE API の試合スコアを付与
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
# .env を開き ANTHROPIC_API_KEY と BALLDONTLIE_API_KEY を記入
```

### 3. バックエンド依存パッケージのインストール

```bash
pip install fastapi uvicorn sqlalchemy apscheduler feedparser requests anthropic python-dotenv
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
| GET | `/api/articles` | 記事一覧取得（category / spurs_only / limit / offset でフィルタ可） |
| GET | `/api/status` | 最終取得日時・使用ソース・API制限状態 |
| POST | `/api/fetch` | バッチ処理の手動実行 |
| GET | `/api/settings` | 設定値取得（ネタバレ防止・Spursフィルタ） |
| PUT | `/api/settings` | 設定値更新 |

---

## 環境変数

`.env.example` を参考に `.env` を作成してください。

| 変数名 | 説明 | 取得先 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API キー | https://console.anthropic.com/ |
| `BALLDONTLIE_API_KEY` | BALLDONTLIE API キー | https://app.balldontlie.io/ |

---

## ログ

```
logs/nba_news.log
```

バッチ実行・RSS取得・Claude API 呼び出し・エラーが記録されます。

---

## ライセンス

個人利用のみを目的としたプロジェクトです。
