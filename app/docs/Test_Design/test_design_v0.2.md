# テスト設計書

- **バージョン**: v0.2
- **ステータス**: Draft
- **作成日**: 2026-05-10
- **更新日**: 2026-05-10
- **対象**: NBAニュース翻訳アプリ（個人利用）
- **参照**:
  - 要件定義書 v0.6（`requirements_v0.6.md`）
  - 基本設計書 v0.4（`basic_design_v0.4.md`）
  - 詳細設計書 v0.1（`detail_design_v0.1.md`）

---

## 1. テスト方針

### 1-1. テスト種別

| 種別 | 対象 | 実施タイミング |
|---|---|---|
| 単体テスト | 各モジュール（関数・クラス単位） | 手順8（製造後） |
| 総合テスト | エンドツーエンドのシナリオ | 手順9（単体テスト後） |

### 1-2. テストツール

| 用途 | ツール |
|---|---|
| バックエンド単体テスト | pytest |
| モック・スタブ | pytest-mock / responses（HTTPモック） |
| フロントエンドテスト | 目視確認（個人利用のため自動UIテスト省略） |
| APIテスト | httpx（FastAPIのTestClient） |

### 1-3. テスト環境

- ローカル環境のみ
- テスト用SQLiteDBを分離（`test.db`）
- 外部API（Claude API・BALLDONTLIE）はモックで代替

---

## 2. 単体テスト設計書

### T-01：RSS正常取得

| 項目 | 内容 |
|---|---|
| **テスト対象** | `fetcher/rss.py` – `fetch_rss()` |
| **目的** | Hoops Rumors RSSが正常に取得・パースできること |
| **前提条件** | Hoops RumorsのRSSフィードをHTTPモックで返す |
| **入力** | モックレスポンス（正常なXML） |
| **期待結果** | `(entries, "hoops_rumors", False)` が返る。entriesが1件以上 |
| **確認方法** | `assert len(entries) > 0` / `assert source == "hoops_rumors"` / `assert is_fallback == False` |

---

### T-02：フェールオーバー（Hoops Rumors障害 → Hoops Wire → The Cold Wire NBA）

| 項目 | 内容 |
|---|---|
| **テスト対象** | `fetcher/rss.py` – `fetch_rss()` |
| **目的** | Hoops Rumors障害時にHoops Wire→The Cold Wire NBAの順で切り替わること |
| **テストケース** | ケース1：Hoops Rumors失敗 → Hoops Wire成功 / ケース2：Hoops Rumors・Hoops Wire失敗 → The Cold Wire NBA成功 / ケース3：全ソース失敗 |
| **ケース1入力** | Hoops Rumors：HTTP 503 / Hoops Wire：正常XML |
| **ケース1期待結果** | `(entries, "hoops_wire", True)` が返る |
| **ケース2期待結果** | `(entries, "the_cold_wire", True)` が返る |
| **ケース3期待結果** | `([], "", True)` が返る |
| **確認方法** | `assert source == "hoops_wire"` / `assert is_fallback == True` |

---

### T-03：重複排除

| 項目 | 内容 |
|---|---|
| **テスト対象** | `db/crud.py` – `exists_article(link)` |
| **目的** | 同一URLの記事が重複保存されないこと |
| **テストケース** | ケース1：新規リンク / ケース2：既存リンク |
| **ケース1入力** | DB未登録のURL |
| **ケース1期待結果** | `exists_article()` が `False` を返す → 保存処理が実行される |
| **ケース2入力** | DB登録済みのURL |
| **ケース2期待結果** | `exists_article()` が `True` を返す → 保存処理がスキップされる |

---

### T-04：Spursフィルタ（categoryタグマッチ）

| 項目 | 内容 |
|---|---|
| **テスト対象** | `processor/filter.py` – `is_spurs_related()` |
| **目的** | `<category>`タグのキーワードマッチが正確に動作すること |
| **テストケース** | ケース1：categoryタグに「Spurs」あり / ケース2：categoryタグに「San Antonio Spurs」あり / ケース3：categoryタグになし・title/descriptionにSpursあり / ケース4：全てなし |
| **ケース1期待結果** | `True` |
| **ケース2期待結果** | `True` |
| **ケース3期待結果** | `True`（フォールバックが機能） |
| **ケース4期待結果** | `False` |

---

### T-05：Claude API正常レスポンス

| 項目 | 内容 |
|---|---|
| **テスト対象** | `processor/claude_client.py` – `process_article()` |
| **目的** | 翻訳・要約・分類が正常なJSON形式で返ること |
| **前提条件** | Claude APIをモックし、正常JSONレスポンスを返すよう設定 |
| **入力** | `title="Spurs sign new guard"`, `description="San Antonio Spurs..."` |
| **期待結果** | `{"title_ja": str, "summary_ja": str, "category": "contract", "has_score": False}` |
| **確認方法** | 各キーの型・categoryの値域（4種類のいずれか）・has_scoreのbool型を検証 |

---

### T-06：カテゴリ分類の境界条件

| 項目 | 内容 |
|---|---|
| **テスト対象** | `processor/claude_client.py` – `process_article()` |
| **目的** | 4分類の境界条件が要件定義書の定義通りに判定されること |
| **テスト方針** | モックを使用（テスト方針§1-3に準拠。実APIを使用しない）。モックが期待するcategoryを返すよう設定し、バリデーション処理・保存処理を検証する |

| ケース | モック設定（返却category） | 入力記事の内容（参考） | 期待結果 |
|---|---|---|---|
| TC-06-1 | `"trade"` | トレード交渉報道 | categoryが`trade`で保存される |
| TC-06-2 | `"contract"` | FA契約金額の報道 | categoryが`contract`で保存される |
| TC-06-3 | `"game"` | 試合速報（スコアが主要情報） | categoryが`game`で保存される |
| TC-06-4 | `"column"` | 試合分析コラム | categoryが`column`で保存される |
| TC-06-5 | `"invalid_value"` | 任意 | バリデーション失敗→英語見出しで保存される |

> **注記：** プロンプト精度の実際の確認（実Claude APIを使った分類精度検証）は、手順10（トライアル運用）で目視確認する。テスト自動化の対象外とする。

---

### T-07：ネタバレ防止（要約にスコアが含まれないこと）

| 項目 | 内容 |
|---|---|
| **テスト対象** | `processor/claude_client.py` – `process_article()` |
| **目的** | `game`カテゴリ判定時、`summary_ja`にスコア・勝敗が含まれないこと |
| **前提条件** | 試合速報記事（スコアを含む）を入力 |
| **確認方法** | `summary_ja` に数字のスコアパターン（例: `\d+-\d+`）や「勝」「敗」「得点」等のキーワードが含まれないことを正規表現で検証 |
| **期待結果** | `summary_ja` がスコア・勝敗を含まない日本語要約であること |

---

### T-08：スコア表示（BALLDONTLIEデータ取得）

| 項目 | 内容 |
|---|---|
| **テスト対象** | `fetcher/score.py` – `fetch_score()` |
| **テストケース** | ケース1：試合あり / ケース2：試合なし / ケース3：API失敗 |
| **ケース1入力** | pubDate: 試合後の日時 / モック：試合データありレスポンス |
| **ケース1期待結果** | `{"game_id": int, "home_team": str, "home_score": int, ...}` が返る |
| **ケース2入力** | pubDate: 試合のない日の日時 / モック：空配列レスポンス |
| **ケース2期待結果** | `None` が返る |
| **ケース3入力** | モック：HTTP 500エラー |
| **ケース3期待結果** | `None` が返る（例外を握りつぶしてNoneを返すこと） |

---

### T-09：API上限管理

| 項目 | 内容 |
|---|---|
| **テスト対象** | `processor/claude_client.py` / `api/routes.py` |
| **目的** | 429エラー時に翻訳スキップ＋`api_limit_exceeded="true"`が設定されること |
| **テストケース** | ケース1：429エラー発生時 / ケース2：月次リセット |
| **ケース1前提条件** | Claude APIモックが `RateLimitError` を返すよう設定 |
| **ケース1期待結果** | `process_article()` が `None` を返す / `api_limit_exceeded` が `"true"` になる |
| **ケース2前提条件** | `api_limit_exceeded="true"` / `api_reset_month` が前月の値 |
| **ケース2期待結果** | バッチ起動時に `api_limit_exceeded="false"` にリセットされる |

---

### T-10：30日超データ自動削除

| 項目 | 内容 |
|---|---|
| **テスト対象** | `db/crud.py` – `delete_old_articles()` |
| **目的** | `fetched_at` が30日超の記事が自動削除されること |
| **前提条件** | 31日前・30日前・29日前のテストデータをDBに挿入 |
| **期待結果** | 31日前のデータのみ削除される。30日前・29日前は残る |
| **確認方法** | `DELETE` 実行後に `SELECT COUNT(*)` で件数を検証 |

---

### T-11：フェールオーバー記録（fetch_logs）

| 項目 | 内容 |
|---|---|
| **テスト対象** | `db/crud.py` – `save_fetch_log()` / バッチ処理全体 |
| **目的** | フェールオーバー発生時に `fetch_logs` に正しく記録されること |
| **前提条件** | Hoops Rumors失敗・Hoops Wire成功のシナリオ |
| **期待結果** | `fetch_logs` に `source_used="hoops_wire"` / `is_fallback=1` / `error_message=NULL` が記録される |

---

### T-12：設定変更の即時反映

| 項目 | 内容 |
|---|---|
| **テスト対象** | `api/routes.py` – `PUT /api/settings` + `GET /api/articles` |
| **目的** | ネタバレ防止・Spursフィルタの設定変更がAPI応答に即座に反映されること |
| **テストケース** | ケース1：`spurs_filter_enabled` を `true` に変更後、`GET /api/articles` で Spurs記事のみ返ること / ケース2：`spoiler_guard_enabled` を変更後、設定値が取得できること |
| **確認方法** | FastAPI `TestClient` を使用してHTTPレベルで検証 |

---

### T-13：パフォーマンス（初期表示速度）

| 項目 | 内容 |
|---|---|
| **テスト対象** | `GET /api/articles` + フロントエンドレンダリング |
| **目的** | DBにデータが存在する状態でのページ初期表示が1秒以内であること |
| **前提条件** | `articles` テーブルに50件程度のデータが存在する |
| **確認方法** | ブラウザのDevToolsでネットワークタブを確認。`/api/articles` のレスポンスタイムが1秒以内であること |
| **期待結果** | APIレスポンスタイム < 1000ms |

---

### T-15：フェールオーバー時Spursフィルタ

| 項目 | 内容 |
|---|---|
| **テスト対象** | `processor/filter.py` – `is_spurs_related()` |
| **目的** | Hoops Wire・The Cold Wire NBA使用時にSpursフィルタが正しく機能すること |
| **テストケース** | ケース1：Hoops Wire形式（`category=["Spurs"]`） / ケース2：The Cold Wire NBA形式（`category=["San Antonio Spurs Rumors And News (Updated Daily)"]`） / ケース3：categoryなし・title/descriptionにSpursあり |
| **ケース1期待結果** | `True`（categoryタグで直接マッチ） |
| **ケース2期待結果** | `True`（categoryタグで部分マッチ） |
| **ケース3期待結果** | `True`（フォールバックでマッチ） |

---

## 3. 総合テスト設計書

### T-14：エンドツーエンドシナリオ

**シナリオ概要：** RSS取得→翻訳・分類→DB保存→画面表示→フィルタ→ネタバレ防止の一連の流れが正常に動作すること

#### シナリオ1：通常バッチ処理 + 画面表示

| ステップ | 操作 | 期待結果 |
|---|---|---|
| 1 | `POST /api/fetch` を実行（手動バッチ起動） | `{"message": "バッチ処理を開始しました"}` が返る |
| 2 | 数秒後に `GET /api/status` を実行 | `last_fetched_at` が現在時刻近辺の値 / `source_used` が `"hoops_rumors"` |
| 3 | `GET /api/articles` を実行 | `articles` に1件以上のデータが返る |
| 4 | 返ってきた記事の `title_ja` を確認 | 日本語の見出しが含まれること |
| 5 | 返ってきた記事の `category` を確認 | `trade` / `contract` / `game` / `column` のいずれかであること |
| 6 | ブラウザでアプリを開く | ニュース一覧が表示されること |

#### シナリオ2：Spursフィルタ

| ステップ | 操作 | 期待結果 |
|---|---|---|
| 1 | フィルタバーで「チームのみ」をONにする | `GET /api/articles?spurs_only=true` が発行される |
| 2 | 表示された記事一覧を確認 | 全記事の `is_spurs` が `true` であること |
| 3 | 「全チーム」に戻す | Spurs以外の記事も表示されること |

#### シナリオ3：ネタバレ防止

| ステップ | 操作 | 期待結果 |
|---|---|---|
| 1 | `category=game` の記事を確認 | 要約がぼかし表示（blur）になっていること |
| 2 | 「スコアを表示」ボタンをクリック | ぼかしが解除されスコアが表示されること（score_dataがある場合） |
| 3 | ネタバレ防止をOFFに切り替える | 全記事の要約がぼかしなしで表示されること |

#### シナリオ4：カテゴリタブ

| ステップ | 操作 | 期待結果 |
|---|---|---|
| 1 | 「トレード」タブをクリック | `category=trade` の記事のみ表示される |
| 2 | 「試合結果」タブをクリック | `category=game` の記事のみ表示される |
| 3 | 「すべて」タブをクリック | 全カテゴリの記事が表示される |

#### シナリオ5：API上限超過時の動作

| ステップ | 操作 | 期待結果 |
|---|---|---|
| 1 | `app_settings.api_limit_exceeded` を `"true"` に手動設定 | — |
| 2 | ブラウザでアプリを開く | ヘッダーにAPI上限バナーが表示されること |
| 3 | 記事一覧を確認 | `title_ja` が英語のまま（原文）・`summary_ja` が空の記事が混在すること |

#### シナリオ6：フェールオーバー動作

| ステップ | 操作 | 期待結果 |
|---|---|---|
| 1 | `config.py` の `RSS_SOURCES[0].url` を無効なURLに変更 | — |
| 2 | バッチを実行する | Hoops Wire（FO1）が使用される |
| 3 | `GET /api/status` を確認 | `source_used="hoops_wire"` / `is_fallback=true` |
| 4 | `fetch_logs` テーブルを確認 | `is_fallback=1` で記録されている |
| 5 | `RSS_SOURCES[0].url` を元に戻す | — |

---

## 4. テスト観点マトリクス

| テストID | 要件ID | 単体 | 総合 | 優先度 |
|---|---|---|---|---|
| T-01 | F-01 | ✅ | ✅（シナリオ1） | 高 |
| T-02 | F-01 | ✅ | ✅（シナリオ6） | 高 |
| T-03 | F-01 | ✅ | — | 高 |
| T-04 | F-04 | ✅ | ✅（シナリオ2） | 高 |
| T-05 | F-02 | ✅ | ✅（シナリオ1） | 高 |
| T-06 | F-03 | ✅ | ✅（シナリオ4） | 高 |
| T-07 | F-05 | ✅ | ✅（シナリオ3） | 高 |
| T-08 | F-05 | ✅ | ✅（シナリオ3） | 高 |
| T-09 | F-07 | ✅ | ✅（シナリオ5） | 中 |
| T-10 | §3非機能 | ✅ | — | 中 |
| T-11 | F-01 | ✅ | ✅（シナリオ6） | 中 |
| T-12 | F-04・F-05 | ✅ | ✅（シナリオ2・3） | 中 |
| T-13 | §3非機能 | — | ✅（シナリオ1） | 中 |
| T-14 | 全体 | —（総合テストにて代替） | ✅（シナリオ1〜6） | 高 |
| T-15 | F-04 | ✅ | ✅（シナリオ6） | 高 |

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v0.1 | 2026-05-10 | 初版作成（基本設計書v0.4のテスト観点T-01〜T-15を単体・総合テストに展開） |
| v0.2 | 2026-05-10 | レビュー指摘を反映。①T-06をモックベースに統一し実API使用方針の矛盾を解消・プロンプト精度検証はトライアル運用での目視確認に変更（軽微-2）、②T-14マトリクス行に「総合テストにて代替」の注記を追加（改善-3） |
