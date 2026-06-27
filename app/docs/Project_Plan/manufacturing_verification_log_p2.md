# 製造フェーズ 動作確認ログ（Phase 2）
## 対象範囲：7-J-0 〜 7-K

---

## 7-J-0：既存 Git / .gitignore 設定の確認

| 項目 | 実施日 | 確認内容 | 結果 | 問題点 |
|------|--------|----------|------|--------|
| 1. .git 正常動作確認 | 2026-06-25 | `git status` が正常応答するか | **Yes** — "On branch master / nothing to commit, working tree clean" | なし |
| 2. ルート .gitignore 必須パターン確認 | 2026-06-25 | 7パターン全て存在するか | **全7パターン揃っている** | なし（詳細は下表） |
| 3. frontend/.gitignore との比較 | 2026-06-25 | 矛盾・重大な重複がないか | **矛盾なし**（軽微な重複あり、問題なし） | 下記「補足」参照 |
| 4. 追跡済みファイルへの混入確認 | 2026-06-25 | `.env`・`*.db`・`__pycache__/`・`node_modules/` が git 管理されていないか | **混入なし** | なし |
| 5. 未コミット変更・未追跡ファイル確認 | 2026-06-25 | `git status` 結果 | **未コミット変更なし、未追跡ファイルなし** | なし |
| 6. コミット履歴確認 | 2026-06-25 | 初回コミット済みか | **Yes**（直近10件確認、最新: f26d05e「フォルダ構成を変更」） | なし |

---

### 2. ルート .gitignore 必須パターン詳細（NBA_news/.gitignore）

| パターン | 存在 |
|---------|------|
| `.env` | ✅ |
| `*.db` | ✅ |
| `__pycache__/` | ✅ |
| `*.pyc` | ✅ |
| `.venv/` | ✅ |
| `node_modules/` | ✅ |
| `logs/` | ✅ |

**判定：全7パターン揃っており、不足なし。**

---

### 3. frontend/.gitignore との比較（app/frontend/.gitignore）

**重複している項目（動作上は問題なし）：**
- `node_modules` / `node_modules/` — 両ファイルに存在。スラッシュ有無の差異のみ、どちらもディレクトリを除外する。
- `dist` / `dist/` — 同上。
- `logs` / `logs/` — 同上（frontend 側はスラッシュなし）。

**frontend/.gitignore が独自に追加しているもの（矛盾なし）：**
- `*.log`、`npm-debug.log*` 等の NPM ログ
- `dist-ssr`、`*.local`
- `.vscode/*`（`!.vscode/extensions.json` 除外）、`.idea`、`*.suo` 等のエディタ設定

**矛盾（除外すべきものを追跡するパターン等）：なし**

---

### 4. 追跡済みファイル混入確認

`git ls-files` で以下を検索した結果：

| 対象 | 追跡ファイル数 | 備考 |
|------|--------------|------|
| `.env` パターン | 0件（機密） | `app/.env.example` のみ追跡（意図通り） |
| `*.db` | 0件 | なし |
| `__pycache__/` 配下 | 0件 | なし |
| `*.pyc` | 0件 | なし |
| `node_modules/` 配下 | 0件 | ディスク上には存在するが git 管理外 |

**判定：機密ファイルの混入なし。正常。**

**補足：** `NBA_news/.env` がルート直下に実在することを確認（内容は参照せず）。  
`.gitignore` の `.env` パターンで正しく除外済みのため、git 追跡対象外。

---

### 5. 未コミット変更・未追跡ファイル一覧

```
On branch master
Your branch is up to date with 'origin/master'.

nothing to commit, working tree clean
```

**未コミット変更：なし / 未追跡ファイル：なし（全ファイルが追跡済みまたは .gitignore で除外済み）**

---

### 6. コミット履歴（直近10件）

```
f26d05e フォルダ構成を変更
3480729 フォルダ構成を変更
81a0dfb プロジェクト計画を修正
b272a61 7-Gを完了
b8188d6 7-Hを完了
f9eb06f 7-Hを完了
fcb215b 7-Hを完了
219f419 7-Gを完了
497f2c2 7-Fを完了
9a7dd39 7-Eを完了
```

**判定：初回コミット済み。リポジトリは正常に運用中。**

---

### 総合判定

| チェック項目 | 結果 |
|-------------|------|
| .git 正常動作 | ✅ Yes |
| 必須7パターン揃い | ✅ 全て存在 |
| frontend との矛盾 | ✅ なし（軽微重複のみ） |
| 機密ファイル混入 | ✅ なし |
| 未コミット変更 | ✅ なし |
| コミット履歴あり | ✅ あり |

**7-J-0 ステータス：完了（問題点なし）**

---

## 7-J-1：README.md / CLAUDE.md のフェーズ2追従更新＋横展開確認

| 項目 | 実施日 | 確認内容 | 結果 | 問題点 |
|------|--------|----------|------|--------|
| 1. README.md カテゴリ記述 | 2026-06-25 | 旧4分類（trade/contract/game/column）→ 現行6タブ構成に更新 | **修正完了** | なし |
| 2. README.md エンドポイント記述 | 2026-06-25 | `GET /api/articles` 削除・現行5エンドポイントに更新 | **修正完了** | なし |
| 3. README.md JWT認証説明 | 2026-06-25 | JWT認証（メモリ保持のみ）の説明を追加 | **追加完了** | なし |
| 4. CLAUDE.md 「外部公開禁止」矛盾記述 | 2026-06-25 | `host="127.0.0.1"・外部公開禁止` → ローカル/本番を区別した記述に修正 | **修正完了** | なし |
| 5. CLAUDE.md 設計書参照パス | 2026-06-25 | 旧パス（docs/detail_design_v0.3.md 等）→ 現行 Phase 2 パスに修正 | **修正完了** | なし |
| 6. CLAUDE.md gameカテゴリ記述 | 2026-06-25 | 廃止済み「gameカテゴリ判定時」→ `has_score=True` ベースの記述に修正 | **修正完了** | なし |
| 7. CLAUDE.md ディレクトリ構成 | 2026-06-25 | Phase 2 新規追加ファイル（auth/、dedup.py、LoginForm.jsx 等）を追記 | **修正完了** | なし |
| 8. 横展開 grep（非 docs/ ファイル） | 2026-06-25 | Phase 1 前提文言の残存確認 | **修正対象なし（詳細は下表）** | なし |
| 9. 簡易動作確認（矛盾解消確認） | 2026-06-25 | CLAUDE.md 修正後に「外部公開禁止」と矛盾した指示が出ないか | **解消確認済み（詳細は下記）** | なし |

---

### 修正内容詳細

#### README.md（app/README.md・NBA_news/README.md の両方を更新）

| 修正箇所 | 変更前 | 変更後 |
|---------|-------|-------|
| AI翻訳・要約 | `claude-haiku` / `300〜500字` | `claude-haiku-4-5-20251001` / `800〜1200字` |
| カテゴリ分類 | `trade/contract/game/column` の4分類 | `trade_fa/draft/injury/column` の4分類 + `is_duplicate=True` 除外 |
| ネタバレ防止 | `試合結果（スコア）を含む記事` | `has_score=True` の記事（全カテゴリ対象）|
| スコア取得 | `game カテゴリの記事に...スコアを付与` | `試合日程取得：専用タブで表示` |
| JWT認証 | 記述なし | JWT認証機能の説明を新規追加 |
| APIエンドポイント | `GET /api/articles`・`POST /api/fetch`・`PUT /api/settings` | `POST /api/auth/login`・`GET /api/news`・`GET /api/schedule` |
| 環境変数 | 2変数（ANTHROPIC・BALLDONTLIE） | 5変数（+SECRET_KEY・USERNAME・USER_PASSWORD）|
| pip install | Phase 1 パッケージのみ | Phase 2 追加分（python-Levenshtein・python-jose・passlib 等）を追加 |

#### CLAUDE.md（app/CLAUDE.md を更新）

| 修正箇所 | 変更前 | 変更後 |
|---------|-------|-------|
| プロジェクト概要 | `（個人利用・ローカルサーバー）` | `（個人利用・著作権法第30条の私的利用範囲で限定公開）` |
| ディレクトリ構成 | auth/・dedup.py なし | auth/（jwt.py・users.py）・dedup.py 追記 |
| フロントコンポーネント | `FilterBar / CategoryTabs / NewsCard 等` | `LoginForm / CategoryTabs / NewsCard / GameSchedule / SpoilerOverlay 等` |
| 設計書パス | `docs/detail_design_v0.3.md` 等 | `docs/Detail_Design/detail_design_p2_v0.4.md` 等（Phase 2 パス）|
| Claude API注記 | `gameカテゴリ判定時は...` | `has_score=Trueと判定した記事の...` |
| セキュリティ節 | `host="127.0.0.1"で起動（外部公開禁止）` | ローカル開発時と Render 本番運用時を区別した記述 |

---

### 横展開 grep 確認結果（非 docs/ ファイル）

`grep -rn "127.0.0.1|外部公開禁止|/api/articles|trade.*contract.*game"` を `app/` 配下の非 docs ファイルに実施した結果：

| ファイル | 発見した文言 | 判定 |
|---------|------------|------|
| `app/CLAUDE.md` | `host="127.0.0.1"で起動（外部公開禁止）` | **今回修正済み** |
| `app/README.md` | `GET /api/articles`・旧カテゴリ記述 | **今回修正済み** |
| `README.md`（ルート） | 同上 | **今回修正済み** |
| `app/backend/main.py:49` | `uvicorn.run(..., host="127.0.0.1", ...)` | **コード。7-J-2で対応予定。報告のみ** |
| `app/frontend/vite.config.js:9` | `target: 'http://127.0.0.1:8000'` | **コード（ローカル開発用プロキシ設定）。7-J-2で対応予定。報告のみ** |
| `app/setup.md:81,96,134` | `http://127.0.0.1:8000` への参照 | **ローカル開発手順として正しい記述。Render運用追記は7-J-2の対象** |
| `setup.md`（ルート） | 同上 | **同上** |
| `app/docs/` 配下の各設計書 | 設計上の記述として多数存在 | **設計書内の歴史的記録。修正対象外** |

**コードへの矛盾コメント・設定の残存はあるが、今回の指示スコープ（ドキュメントのみ）の範囲外。7-J-2 での対応を待つ。**

---

### 簡易動作確認（CLAUDE.md 修正後の矛盾解消確認）

現在このCLAUDE.mdは更新済みの状態でClaude Codeに読み込まれている。セキュリティ節の内容は：
- ローカル開発時：`host="127.0.0.1"` 使用
- Render本番運用時：`host="0.0.0.0"` + CORS環境変数化（7-J-2で対応）

「現在の公開方針を説明してください」と問われた場合、CLAUDE.md を参照したClaude Codeは「ローカルと本番を区別」した回答が可能な状態になっており、旧来の「外部公開禁止」という単一ルールは削除済みであることを確認。

---

### 総合判定

| チェック項目 | 結果 |
|-------------|------|
| README.md カテゴリ・エンドポイント記述が現行と一致 | ✅ 修正済み |
| CLAUDE.md「外部公開禁止」矛盾記述の解消 | ✅ 修正済み |
| 横展開 grep 結果（残存箇所の一覧化） | ✅ 確認完了（コード残存は7-J-2対応予定として報告） |
| 修正後の矛盾解消確認 | ✅ 確認済み |

**7-J-1 ステータス：完了**

---

## 7-J-2：Render公開インフラ構築

| 項目 | 実施日 | 確認内容 | 結果 | 問題点 |
|------|--------|----------|------|--------|
| 1. main.py host/port 環境変数化 | 2026-06-26 | `HOST`/`PORT` 環境変数対応・ローカルデフォルト値維持 | **完了** | なし |
| 2. main.py CORS ミドルウェア追加 | 2026-06-26 | `ALLOWED_ORIGINS` 環境変数・ローカルデフォルト `localhost:5173` | **完了** | なし |
| 3. /healthz エンドポイント追加 | 2026-06-26 | 認証不要・DBアクセスなし・`{"status":"ok"}` を返す | **完了** | なし |
| 4. backend/runtime.txt 新規作成 | 2026-06-26 | `python-3.11.9` を記載 | **完了** | なし |
| 5. frontend/package.json engines 追加 | 2026-06-26 | `"node": ">=22.0.0"` を追加 | **完了** | なし |
| 6. render.yaml 新規作成 | 2026-06-26 | 2サービス構成・5項目 sync:false・秘密値なし | **完了** | なし |
| 7. setup.md Render運用手順追記 | 2026-06-26 | 手順A〜E（連携・環境変数・URL更新・Disk確認・動作確認）を追記 | **完了** | なし |
| 8. フロントエンドAPIベースURL対応 | 2026-06-26 | `VITE_API_BASE_URL` 環境変数対応（useAuth/useNews/GameSchedule） | **完了** | なし（詳細は下記） |

---

### 実装内容詳細

#### (A) backend/main.py 変更点

| 変更箇所 | 変更内容 |
|---------|---------|
| import | `from fastapi.middleware.cors import CORSMiddleware` を追加 |
| CORS設定 | `ALLOWED_ORIGINS` 環境変数からオリジンリストを生成（未設定時デフォルト: `http://localhost:5173`） |
| CORSMiddleware | `allow_credentials=True`・`allow_methods=["*"]`・`allow_headers=["*"]` で登録 |
| `/healthz` | 認証不要・DBアクセスなしの専用エンドポイントを追加（Renderのヘルスチェックパスに使用） |
| uvicorn.run | `host=os.getenv("HOST", "127.0.0.1")`・`port=int(os.getenv("PORT", 8000))` に変更 |
| ローカル開発の後方互換性 | `HOST`/`PORT`/`ALLOWED_ORIGINS` いずれも未設定時に従来通りの値をデフォルトとして使用 |

#### (B) 新規ファイル

| ファイル | 内容 |
|---------|------|
| `app/backend/runtime.txt` | `python-3.11.9` |
| `render.yaml`（リポジトリルート） | 2サービス構成（Web Service + Static Site） |

#### (C) render.yaml 構成サマリー

| 項目 | バックエンド（Web Service） | フロントエンド（Static Site） |
|-----|--------------------------|---------------------------|
| plan | starter | — |
| buildCommand | `pip install -r app/backend/requirements.txt` | `cd app/frontend && npm install && npm run build` |
| startCommand | `cd app/backend && python main.py` | — |
| healthCheckPath | `/healthz` | — |
| disk | `mountPath: /data`・`sizeGB: 1` | — |
| staticPublishPath | — | `app/frontend/dist` |
| routes | — | SPA用 `/* → /index.html` rewrite |

**シークレット5項目（sync: false・値なし）：**
`ANTHROPIC_API_KEY`・`BALLDONTLIE_API_KEY`・`SECRET_KEY`・`USERNAME`・`USER_PASSWORD`

**通常値：**
`DATABASE_URL=/data/nba_news.db`・`ALLOWED_ORIGINS`（プレースホルダー）・`VITE_API_BASE_URL`（プレースホルダー）

#### (D) フロントエンドAPIベースURL管理

**発見した状況：** 全API呼び出しが相対パス（`/api/...`）を使用。ローカル開発ではViteプロキシが機能するが、Render Static Site（別オリジン）では動作しない。

**対応：** `VITE_API_BASE_URL` 環境変数を以下3ファイルに追加：

| ファイル | 変更内容 |
|---------|---------|
| `useAuth.js` | `const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''` 追加・`/api/auth/login` を更新 |
| `useNews.js` | 同上・`/api/news`・`/api/status`・`/api/settings`（2箇所）を更新 |
| `GameSchedule.jsx` | 同上・`/api/schedule` を更新 |

**ローカル開発への影響：** `VITE_API_BASE_URL` 未設定時は `''`（空文字）がデフォルトのため、相対パスのままViteプロキシが動作する。挙動変更なし。

---

### セルフチェック

| チェック項目 | 結果 |
|-------------|------|
| main.py host/port/CORSが環境変数化・ローカルデフォルト維持 | ✅ |
| /healthz が認証なしで `{"status":"ok"}` を返す（コード確認済み） | ✅ |
| render.yaml に秘密値なし・5項目が sync:false（grep確認済み） | ✅ |
| runtime.txt・package.json engines 追加 | ✅ |
| setup.md に Render 運用手順追記（手順A〜E） | ✅ |
| フロントエンドAPIベースURL管理の報告と対応 | ✅ |

**7-J-2 ステータス：完了**

---

## ヘルスチェック失敗の調査・修正（render.yaml HOST設定追加）

### 調査結果

| 原因 | 内容 | 評価 |
|-----|------|------|
| 想定原因1：HOST環境変数未設定 | `main.py` は `host=os.getenv("HOST", "127.0.0.1")` であり、`render.yaml` に `HOST` 未設定の場合 `127.0.0.1` にバインドされる。Renderのヘルスチェック（コンテナ外部からの接続）が到達できず必ずタイムアウトする | **最有力・修正対象** |
| 想定原因2：ヘルスチェックパス不一致 | `render.yaml` の `healthCheckPath: /healthz`（9行目） ↔ `main.py` の `@app.get("/healthz")`（44行目）— 完全一致 | **問題なし** |

### 修正内容

**render.yaml のバックエンド `envVars` に `HOST: 0.0.0.0` を追加（通常値セクション）**

```yaml
- key: HOST
  value: 0.0.0.0
```

### セルフチェック

| チェック項目 | 結果 |
|-------------|------|
| `render.yaml` に `HOST: 0.0.0.0` が追加されているか | ✅ 追加済み（通常値セクション） |
| `healthCheckPath` が `/healthz` と完全一致しているか | ✅ render.yaml 9行目 ↔ main.py 44行目 |
| `PORT` がRender自動注入値をそのまま使用（ハードコードなし）か | ✅ `int(os.getenv("PORT", 8000))` |
| 秘密値が誤って追加されていないか | ✅ `HOST: 0.0.0.0` は非秘密・非 sync:false で正しい |
| 再デプロイ後、ヘルスチェックが成功したか（RenderダッシュボードでLiveになるか） | ⬜ 再デプロイ後に確認要 |

---

## 7-J-3：実デプロイ確認

| 項目 | 実施日 | 確認内容 | 結果 | 問題点 |
|------|--------|----------|------|--------|
| 1. Render Blueprint作成 | 2026-06-27 | Static Site定義の `type: static` エラーを `type: web` + `env: static` に修正し解消 | **完了** | なし |
| 2. バックエンドヘルスチェックタイムアウト解消 | 2026-06-27 | `HOST=0.0.0.0` が `render.yaml` に未設定だったため追加し解消 | **完了** | なし |
| 3. DBパス設定ミス修正 | 2026-06-27 | `DATABASE_URL` 環境変数の値を訂正し、再起動後 `init_user()` が正常に初回ユーザーを作成 | **完了** | なし |
| 4. ログインAPI確認 | 2026-06-27 | `POST /api/auth/login`：正しい認証情報で 200 応答 | **完了** | なし |
| 5. 認証必須エンドポイント確認 | 2026-06-27 | `GET /api/news`：トークン付きで 200、トークンなしで 401/403 応答 | **完了** | なし |
| 6. フロントエンド実機確認 | 2026-06-27 | `https://nba-news-frontend.onrender.com` からログイン・ニュース一覧表示が正常動作、ブラウザ Console に CORS エラーなし | **完了** | なし |
| 7. Persistent Diskデータ保持確認 | 2026-06-27 | バックエンド再起動後も記事件数が保持されていることを確認 | **完了** | なし |

---

### 総合判定

| チェック項目 | 結果 |
|-------------|------|
| Render Blueprint 作成（`type: web` + `env: static` 修正） | ✅ |
| ヘルスチェックタイムアウト解消（`HOST=0.0.0.0` 追加） | ✅ |
| DBパス設定ミス修正・`init_user()` 正常動作 | ✅ |
| ログインAPI（`POST /api/auth/login`）200応答 | ✅ |
| 認証必須エンドポイント（トークン付き200・なし401/403） | ✅ |
| フロントエンド実機確認（ログイン・一覧表示・CORSエラーなし） | ✅ |
| Persistent Disk データ保持確認（再起動後も記事件数維持） | ✅ |

**7-J-3 ステータス：完了**
