# Render手動デプロイ手順書（フェーズ2・7-J-3用）

- **バージョン**: v1.0
- **作成日**: 2026-06-26
- **対象**: 7-J-3「実デプロイ確認」のうち、Renderダッシュボード上でTakumi様が手動実施する作業
- **前提**: 7-J-0〜7-J-2が完了済み（`render.yaml`がリポジトリルートに存在し、シークレット値は一切含まれていないことを確認済み）

---

## 0. 事前に準備するもの

| 項目 | 内容 |
|---|---|
| GitHubアカウント | リポジトリ（`NBA_news`）がpush可能な状態であること |
| Renderアカウント | [https://dashboard.render.com](https://dashboard.render.com) でログイン可能なこと（未作成ならGitHub連携で新規登録） |
| `.env`の内容 | `ANTHROPIC_API_KEY`・`BALLDONTLIE_API_KEY`・`SECRET_KEY`・`USERNAME`・`USER_PASSWORD`の5項目（手元の`.env`に控えがあるはず） |
| `SECRET_KEY`の生成（未生成の場合） | ローカルで`openssl rand -hex 32`を実行し控えておく |

**注意：** この手順書および以降の作業ログに、上記5項目の実際の値を書き込まないこと。値はRenderダッシュボード上で直接入力する。

---

## 1. GitHubへpush

1. ローカルで`git status`を実行し、7-J-0〜7-J-2の変更（`render.yaml`・`main.py`・`runtime.txt`・`package.json`・`setup.md`等）がコミット済みであることを確認する。
2. 未コミットであれば`git add`→`git commit`（コミットメッセージ例：「7-J-2完了：Render公開インフラ構築」）。
3. `git push origin master`（またはmainブランチ名に合わせる）でGitHubにpushする。

---

## 2. Renderで新規Blueprintを作成

1. [https://dashboard.render.com](https://dashboard.render.com) にログイン。
2. 右上の **New** ボタン → **Blueprint** を選択。
3. 対象のGitHubリポジトリ（`NBA_news`）を選択し、連携を許可する（初回はGitHub認証画面が出る）。
4. Renderがリポジトリルートの`render.yaml`を自動検出し、2サービス（Web Service・Static Site）の構成案を表示する。内容を確認し、**Apply**（または**Create New Resources**）をクリックする。
5. この時点でビルドが開始されるが、シークレット5項目が未設定のためバックエンドは起動に失敗する（`config.py`が`RuntimeError`を出す想定通りの挙動）。次の手順で設定する。

---

## 3. シークレット5項目をバックエンドサービスに設定

1. Renderダッシュボードでバックエンドのサービス（Web Service）を開く。
2. 左メニューの **Environment** タブを選択する。
3. `render.yaml`で`sync: false`指定した5項目が「未設定」として一覧表示されているはずなので、それぞれに値を入力する：
   - `ANTHROPIC_API_KEY` → 手元の`.env`の値を入力
   - `BALLDONTLIE_API_KEY` → 同上
   - `SECRET_KEY` → 同上（未生成なら`openssl rand -hex 32`で生成した値）
   - `USERNAME` → ログインに使うユーザー名
   - `USER_PASSWORD` → ログインに使うパスワード（強力なものを設定）
4. **Save Changes**をクリックする（自動的に再デプロイが始まる）。

---

## 4. デプロイ完了・URLの確認

1. バックエンドサービスの画面上部に表示される稼働状況が **Live**（緑）になるまで待つ（数分かかる場合がある）。ログタブでエラーが出ていないか確認する。
2. バックエンドのURL（画面上部、`https://〇〇.onrender.com`の形式）をメモする。
3. フロントエンド（Static Site）のサービス画面でも同様にビルド完了・**Live**を確認し、URLをメモする。
4. この時点ではフロントエンドからバックエンドへのAPI呼び出しはCORSエラーで失敗する（`ALLOWED_ORIGINS`がまだフロントエンドの実URLを向いていないため）。次の手順で設定する。

---

## 5. `ALLOWED_ORIGINS`・`VITE_API_BASE_URL`を実URLに更新

1. バックエンドサービスの **Environment** タブで、`ALLOWED_ORIGINS`の値を手順4でメモしたフロントエンドのURL（例：`https://yyy.onrender.com`）に変更する。複数オリジンがある場合はカンマ区切り。
2. フロントエンド（Static Site）サービスの **Environment** タブで、`VITE_API_BASE_URL`の値を手順4でメモしたバックエンドのURL（例：`https://xxx.onrender.com`）に変更する。
3. 両方とも**Save Changes**を押し、再デプロイを待つ（フロントエンドはビルド時に環境変数を埋め込むため、再ビルドが必須）。
4. 両サービスが再度**Live**になったことを確認する。

---

## 6. Claude Codeへ引き渡す情報

以下をClaude Codeに渡し、7-J-3の動作確認（`/healthz`・ログイン・API応答・CORS確認）を実施させる。

- バックエンドURL：`https://〇〇.onrender.com`
- フロントエンドURL：`https://△△.onrender.com`

**渡してはいけない情報：** `USERNAME`・`USER_PASSWORD`・`SECRET_KEY`等の実際の値（Claude Codeにログイン確認をさせる場合も、値そのものは会話・ログに残さない運用とする）。

---

## 7. うまくいかない場合のチェックポイント

| 症状 | 確認箇所 |
|---|---|
| バックエンドが起動しない（Live にならない） | Environmentタブで5項目が全て入力済みか／ログタブで`RuntimeError`の内容を確認 |
| フロントエンドからAPIを呼ぶとCORSエラー | `ALLOWED_ORIGINS`がフロントエンドの実URLと完全一致しているか（末尾スラッシュの有無等） |
| ログイン後も記事が表示されない | `VITE_API_BASE_URL`がフロントエンドの再ビルドに反映されているか（再デプロイ忘れ） |
| 再起動後に記事データが消える | Persistent Diskが正しくマウントされているか（Disksタブで`/data`・1GBの設定を確認） |

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v1.0 | 2026-06-26 | 初版作成（7-J-3向け手動デプロイ手順書） |
