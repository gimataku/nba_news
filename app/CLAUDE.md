# CLAUDE.md

## プロジェクト概要
NBAニュース翻訳アプリ（個人利用・著作権法第30条の私的利用範囲で限定公開）
海外NBAニュースのRSSを定時取得し、Claude APIで日本語要約・カテゴリ分類して表示する。フェーズ2でJWT認証を追加しRender経由で限定公開する。

## 技術スタック
- バックエンド：Python 3.11 / FastAPI / SQLite3 / APScheduler / feedparser / requests
- フロントエンド：React 18 / Vite / Tailwind CSS
- 外部API：Claude API（claude-haiku-4-5-20251001）/ BALLDONTLIE API / RSS

## ディレクトリ構成
'''
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
│   │   │   ├── dedup.py          # 重複排除（Levenshtein距離80%閾値）
│   │   │   └── filter.py         # Spurs 関連フィルタ
│   │   ├── auth/
│   │   │   ├── jwt.py            # JWT認証
│   │   │   └── users.py          # ユーザー管理
│   │   ├── db/
│   │   │   ├── models.py      # テーブル定義・DB初期化
│   │   │   └── crud.py        # CRUD 操作
│   │   ├── api/
│   │   |   ├── routes.py      # FastAPI ルーティング
│   ├── frontend/
│   │   └── src/
│   │       ├── App.jsx
│   │       └── components/    # LoginForm / CategoryTabs / NewsCard / GameSchedule / SpoilerOverlay 等
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
'''

## 設計書（必ず参照すること）
- 詳細設計書：docs/Detail_Design/detail_design_p2_v0.4.md
- 基本設計書：docs/Basic_Design/basic_design_p2_v0.5.md
- 要件定義書：docs/Requirement/requirements_p2_v0.12.md

## 実装上の重要な注意事項

### RSS取得
- feedparser.parse()は直接使用禁止。必ずrequests.get()でコンテンツ取得後にfeedparser.parse(response.content)へ渡す
- タイムアウトは(5, 10)（接続5秒・読み取り10秒）
- フェールオーバー順：Hoops Rumors → Hoops Wire → The Cold Wire NBA

### DB設計
- source_urlカラムはarticlesテーブルに存在しない
- APIレスポンス生成時にlinkカラムをsource_urlとして返す
  例：{"source_url": article["link"]}

### Claude API
- モデル：claude-haiku-4-5-20251001
- 1記事1リクエストで翻訳・要約・カテゴリ分類・has_scoreをまとめて処理
- has_score=Trueと判定した記事のsummary_jaにはスコア・勝敗を含めない（ネタバレ防止）
- RateLimitError（429）→ api_limit_exceeded="true"設定・当該記事をスキップ（DB保存しない）
- JSONDecodeError・バリデーション失敗 → title_ja=title_original・summary_ja=NULL・category=NULL・has_score=Falseで保存

### スケジューラ
- APSchedulerで10分ごとにチェック
- last_fetched_at=""（初回）または前回取得から4時間経過で実行
- cron方式は使用しない

### セキュリティ
- APIキーは.envから読む。ハードコード禁止
- ローカル開発時はhost="127.0.0.1"で起動
- Render本番運用時はJWT認証を前提にhost="0.0.0.0"・CORS設定を環境変数化して外部公開する（7-J-2で対応）

### ログ
- main.py起動時にos.makedirs("logs", exist_ok=True)を実行
- ログ出力先：logs/nba_news.log