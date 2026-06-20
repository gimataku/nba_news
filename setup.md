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
