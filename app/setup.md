# NBA News JP セットアップ手順

## 前提条件

- Python 3.11 以上
- Node.js 18 以上
- ANTHROPIC_API_KEY（[Anthropic Console](https://console.anthropic.com/) から取得）
- BALLDONTLIE_API_KEY（[balldontlie.io](https://www.balldontlie.io/) から取得）

---

## 1. バックエンドのセットアップ

リポジトリルート（`NBA_news/`）から実行する：

```
cd app/backend
python -m venv venv
```

仮想環境を有効化する：

- **Windows**:
  ```
  venv\Scripts\activate
  ```
- **Mac / Linux**:
  ```
  source venv/bin/activate
  ```

依存パッケージをインストールする：

```
pip install -r requirements.txt
```

---

## 2. 環境変数の設定

`app/backend/.env` を新規作成し、以下の5項目をすべて設定する：

```
ANTHROPIC_API_KEY=sk-ant-xxxxx
BALLDONTLIE_API_KEY=xxxxx
SECRET_KEY=（下記コマンドで生成した値を貼り付ける）
USERNAME=任意のログインユーザー名
USER_PASSWORD=任意のログインパスワード
```

`SECRET_KEY` は以下のコマンドで生成する（OpenSSL が必要）：

```
openssl rand -hex 32
```

> **重要**: `SECRET_KEY` / `USERNAME` / `USER_PASSWORD` のいずれかが未設定または空文字の場合、
> バックエンド起動時に `RuntimeError` が発生してサービスが起動しません。

---

## 3. バックエンドの起動

仮想環境を有効化した状態で、`app/backend/` ディレクトリから実行する：

```
python main.py
```

起動成功時のログ出力例：

```
INFO  DB initialized
INFO  Initial user check completed
INFO  Scheduler started
```

- 初回起動時に `app/backend/nba_news.db` が自動作成される
- `app/backend/logs/nba_news.log` にもログが書き出される
- バックエンドは `http://127.0.0.1:8000` で起動する

---

## 4. フロントエンドのセットアップ・起動

新しいターミナルを開き、リポジトリルートから実行する：

```
cd app/frontend
npm install
npm run dev
```

- フロントエンドは `http://localhost:5173` で起動する
- `/api` へのリクエストはバックエンド（`http://127.0.0.1:8000`）へ自動プロキシされる

---

## 5. 動作確認

1. バックエンドとフロントエンドの両方を起動した状態で、ブラウザで `http://localhost:5173` を開く
2. ログインフォームが表示されることを確認する
3. 手順 2 で設定した `USERNAME` / `USER_PASSWORD` でログインする
4. ニュース一覧画面に遷移すれば正常に動作している

---

## トラブルシューティング

### RuntimeError: SECRET_KEY が未設定です

`app/backend/.env` に `SECRET_KEY=` の行が存在するか確認してください。
値が空文字の場合も同じエラーになります。`openssl rand -hex 32` で生成した値を設定してください。

### RuntimeError: USERNAME / USER_PASSWORD が未設定です

`app/backend/.env` に `USERNAME=` と `USER_PASSWORD=` が両方設定されているか確認してください。

### ポート 8000 が使用中

別プロセスがポート 8000 を使用しています。以下でプロセスを確認して終了してください：

- **Windows**: `netstat -ano | findstr :8000` でPIDを確認 → `taskkill /PID <PID> /F`
- **Mac / Linux**: `lsof -i :8000` でPIDを確認 → `kill <PID>`

### ポート 5173 が使用中

Vite は空きポートを自動的に探して起動します（例: 5174, 5175...）。
ターミナルに表示された URL を使用してください。

### ログインできない

- バックエンドが起動していることを確認してください（`http://127.0.0.1:8000/docs` にアクセスできるか）
- `.env` の `USERNAME` / `USER_PASSWORD` に設定した値を正確に入力しているか確認してください
- DB を削除して再起動すると初回ユーザーが再作成されます：
  - **Windows**: `del app\backend\nba_news.db`
  - **Mac / Linux**: `rm app/backend/nba_news.db`
  - その後 `python main.py` で再起動

---

## Render 本番運用手順

> **前提**: ローカル開発が正常に動作していること（手順1〜5 が完了していること）。

### Render 構成概要

本アプリはリポジトリルート（`NBA_news/`）の `render.yaml` で2サービス構成を定義している：

| サービス | 種別 | 役割 |
|---|---|---|
| `nba-news-backend` | Web Service（Starter $7/月） | Python/FastAPI バックエンド + Persistent Disk（1GB $0.25/月） |
| `nba-news-frontend` | Static Site（無料） | React フロントエンド |

### 手順 A：GitHubリポジトリとRenderの連携

1. [Render ダッシュボード](https://dashboard.render.com/) にログインする
2. 「New +」→「Blueprint」を選択し、このリポジトリを連携する
3. Render が `render.yaml` を自動検出し、2サービスの構成を表示する
4. 確認後「Apply」でサービスを作成する

### 手順 B：シークレット環境変数の手動入力

`render.yaml` にはセキュリティ上 `sync: false` として値を記載していない。以下5項目を Render ダッシュボードの **`nba-news-backend` サービス → Environment → Environment Variables** で手動入力すること：

| 変数名 | 値の取得方法 |
|---|---|
| `ANTHROPIC_API_KEY` | [Anthropic Console](https://console.anthropic.com/) |
| `BALLDONTLIE_API_KEY` | [balldontlie.io](https://www.balldontlie.io/) |
| `SECRET_KEY` | `openssl rand -hex 32` で生成 |
| `USERNAME` | 任意のログインユーザー名 |
| `USER_PASSWORD` | 任意のログインパスワード |

> **重要**: 5項目のいずれかが未設定または空文字の場合、バックエンドは起動時に `RuntimeError` を発生させ起動しません。

### 手順 C：URL プレースホルダーの更新

初回デプロイ後、Render が各サービスのURLを払い出す（例: `https://nba-news-backend.onrender.com`）。以下の2箇所を実際のURLに更新すること：

1. **バックエンドの `ALLOWED_ORIGINS` 環境変数**  
   `nba-news-backend` → Environment → `ALLOWED_ORIGINS` の値を フロントエンドの実際のURL に変更  
   例: `https://nba-news-frontend.onrender.com`

2. **フロントエンドの `VITE_API_BASE_URL` 環境変数**  
   `nba-news-frontend` → Environment → `VITE_API_BASE_URL` の値を バックエンドの実際のURL に変更  
   例: `https://nba-news-backend.onrender.com`  
   変更後は **Manual Deploy** でフロントエンドを再ビルドすること（ビルド時環境変数のため）。

### 手順 D：Persistent Disk の確認

`nba-news-backend` → Disks で以下の設定が適用されているか確認する：

- **Name**: `nba-news-data`
- **Mount Path**: `/data`
- **Size**: 1 GB

SQLite DB は `/data/nba_news.db` に保存され、デプロイ後もデータが保持される。

### 手順 E：デプロイ後の動作確認

1. **ヘルスチェック確認**  
   バックエンドURL + `/healthz` にアクセスし `{"status":"ok"}` が返ることを確認する  
   例: `https://nba-news-backend.onrender.com/healthz`

2. **ログイン確認**  
   フロントエンドURL（例: `https://nba-news-frontend.onrender.com`）を開き、手順Bで設定した `USERNAME` / `USER_PASSWORD` でログインできることを確認する

3. **記事取得確認**  
   ログイン後、ニュース一覧画面が表示されること（初回バッチ実行まで記事は0件の場合あり）を確認する
