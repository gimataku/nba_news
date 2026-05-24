# 環境構築手順

## 1. 前提条件

以下のソフトウェアが事前にインストールされていること。

- Python 3.11 以上
- Node.js 18 以上

## 2. リポジトリのクローン

```bash
git clone <リポジトリURL>
cd NBA_news
```

## 3. .env ファイルの準備

`.env.example` をコピーして `.env` を作成し、各APIキーを記入する。

```bash
cp .env.example .env
```

`.env` を開き、`ANTHROPIC_API_KEY` および `BALLDONTLIE_API_KEY` に取得したキーを設定する（取得先は末尾を参照）。

## 4. バックエンドの依存パッケージインストール

```bash
pip install fastapi uvicorn sqlalchemy apscheduler feedparser requests anthropic python-dotenv
```

## 5. フロントエンドの依存パッケージインストール

```bash
cd frontend && npm install
```

## 6. バックエンドの起動

```bash
cd backend && python main.py
```

## 7. フロントエンドの起動

```bash
cd frontend && npm run dev
```

## 8. アクセス方法

バックエンドとフロントエンドの両方を起動した状態で、ブラウザで以下のURLを開く。

```
http://localhost:5173
```

## 9. ログの確認

アプリケーションのログは以下のファイルに出力される。

```
logs/nba_news.log
```

## 10. APIキーの取得先

| サービス | 取得先URL |
|---|---|
| Anthropic API Key | https://console.anthropic.com/ |
| BALLDONTLIE API Key | https://app.balldontlie.io/ |
