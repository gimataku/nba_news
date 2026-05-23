# リスク調査レポート

- **バージョン**: v0.5
- **ステータス**: 完了
- **作成日**: 2026-05-10
- **更新日**: 2026-05-10
- **対象**: NBAニュース翻訳アプリ（個人利用）
- **参照**: プロジェクト計画書 v0.2（`project_plan_v0.2.md`）、要件定義書 v0.6（`requirements_v0.6.md`）

---

## サマリー

| 区分 | 判定 | 概要 |
|---|---|---|
| 法的リスク | ✅ 条件付き適法 | Hoops Rumors・HoopsHype等の代替ソースはESPNより規約が緩やか。要約独自生成方式で対応可能。日本著作権法の詳細は手順5（リスク正式評価）で対処 |
| コストリスク | ✅ 低リスク | ニュースRSS・BALLDONTLIE API（gamesエンドポイント）はすべて無料。Claude APIは月額$5程度（Haiku 4.5使用） |
| 技術リスク | ✅ 解消 | RSS実機確認・BALLDONTLIE動作確認がともに完了。Spursフィルタはキーワードマッチで実現可能と確認済み |

**設計着手の判断：✅ 基本設計（手順3）に進んでよい**
基本設計着手前の必須事項（RSS実機確認・BALLDONTLIE動作確認）がともに完了した。残存リスクはHoops Rumors1本化によるソース障害リスクのみで、基本設計でフェールオーバー設計を行うことで対処する。

---

## v0.1からv0.2への変更経緯（差分サマリー）

v0.1ではESPNを主要ソースとして調査を進めたが、以下の2つの致命的問題が判明したためESPNを除外した。

| 問題 | 内容 |
|---|---|
| 利用規約「改変禁止」 | "You may not modify any content provided in the feed, including but not limited to story headlines, story summaries, or URLs."（出典：[ESPN RSS Index](https://www.espn.com/espn/news/story?id=3437834)）。翻訳・要約がこれに該当する可能性があり除外 |
| チーム名タグなし | ESPNのRSSにはチーム識別用のメタタグが含まれず、Spursフィルタの実装が困難 |

v0.2ではHoops Rumors・RealGM等の代替ソースとBALLDONTLIE APIを新たに調査した。

---

## 1. 法的調査

### 1-1. ESPNを除外する理由（確定）

| 理由 | 内容 | 出典 |
|---|---|---|
| 利用規約「改変禁止」 | "You may not modify any content provided in the feed, including but not limited to story headlines, story summaries, or URLs." | [ESPN RSS Index](https://www.espn.com/espn/news/story?id=3437834) |
| チーム名タグなし | RSSフィードには標準的なチーム名タグが含まれず、フィルタ実装が困難 | v0.1調査 |

---

### 1-2. 代替ニュースソース一覧と利用規約

| ソース | RSS URL | 特徴 | 規約リスク |
|---|---|---|---|
| **Hoops Rumors** | `hoopsrumors.com/feed` | トレード・FA特化。週50件以上 | ✅ 低（後述） |
| **HoopsHype** | `hoopshype.com/feed` | Gannett傘下。契約・サラリー強い | ⚠️ 中（後述） |
| ~~RealGM~~ | ~~`basketball.realgm.com/rss/wiretap.rss`~~ | ~~ニュース・スタッツ網羅~~ | **❌ RSS 404のため除外確定**（実機確認済み） |
| **The Cold Wire NBA** | `thecoldwire.com/sports/nba/feed` | 一般NBAニュース | ✅ 低 |
| **Hoops Wire** | `hoopswire.com/feed` | トレード・ドラフト情報 | ✅ 低 |

#### Hoops Rumors の利用規約

公開されている規約はコメントポリシーとプライバシーポリシーのみで、RSS利用に関する明示的な禁止条項は確認できなかった。

- プライバシーポリシー：Google広告のCookieポリシーのみ。RSS規制なし
- コメントポリシー：コメント投稿のルールのみ

**出典：** [About Hoops Rumors](https://www.hoopsrumors.com/2011/11/about-hoops-rumors.html)、[Privacy Policy](https://www.hoopsrumors.com/2012/01/hoopsrumorscom-privacy-policy.html)

**判定：✅ RSS個人利用は問題なし。** ただし以下を遵守する：元記事へのリンクを必ず表示、Hoops Rumorsのクレジット表示、商業的利用は不可。

#### HoopsHype の利用規約

2012年にUSA Today Sports Media Group（Gannett Co.傘下）に買収。RSS個人利用の明示的な禁止は確認できなかったが、大手メディア傘下であるため規約厳格化のリスクがある。

**出典：** [Wikipedia - HoopsHype](https://en.wikipedia.org/wiki/HoopsHype)、[HoopsHype Help Center](https://help.hoopshype.com/)

**判定：⚠️ 補助的使用に限定する。** 主軸はHoops Rumorsに置く。

#### 推奨ニュースソース構成（実機確認後・確定版）

| 役割 | ソース | 主な取得コンテンツ | 備考 |
|---|---|---|---|
| **主軸** | Hoops Rumors RSS | トレード噂・サイン・FA動向 | `<category>`タグでSpursフィルタ可能（実機確認済み） |
| **補助（フェールオーバー）** | HoopsHype RSS | 契約詳細・サラリー情報 | Hoops Rumors障害時のバックアップ |

> **⚠️ RealGMはRSSフィードが404のため除外確定（実機確認済み）。** ニュースソースが実質Hoops Rumors1本になったため、HoopsHypeをフェールオーバー用補助ソースとして位置付ける。The Cold Wire NBA・Hoops Wireは追加候補として残存（基本設計で追加要否を判断）。

---

### 1-3. NBA.com 利用規約（全文精読結果）

**出典：** [NBA.com Terms of Use §1, §7, §9](https://www.nba.com/termsofuse)（最終更新：2023年2月20日）

| 条項 | 内容 |
|---|---|
| §1 利用制限 | 個人の非商業的利用に限りダウンロード可。書面許可なしに複製・改変・再公開等は禁止 |
| §7 モジュールコンテンツ（RSS含む） | RSSを含むコンテンツの「抜粋・編集」は禁止（Operatorが明示許可した場合を除く） |
| §9 NBAスタッツ | 個人・非商業・NBA.com出典表示の3条件を満たせば利用可能 |

| 項目 | 判定 | 理由 |
|---|---|---|
| NBA.com RSSをニュースソースとして使用 | ❌ 非推奨 | 「抜粋・編集禁止」がESPNと同様の問題を生じる |
| NBA.comスタッツの参照 | ✅ 条件付き可 | 個人・非商業・出典表示の3条件を守ること |

**結論：NBA.comはニュース記事の取得には使用しない。スタッツの補足参照に限定し、出典を明示する。**

---

### 1-4. 日本著作権法における翻訳・要約の扱い

**調査範囲の宣言：** 本調査では基本的な法的枠組みを確認した。詳細な法的評価は手順5（リスク正式評価）で対処する。

**根拠条文：著作権法 第47条の6**

個人的または家庭内等の閉鎖的範囲内での使用目的であれば、翻訳・編曲・変形・翻案も許容される。

**裁判例：「血液型と性格」要約引用事件（東京地判平成10年10月30日）**

やむを得ない範囲での要約引用は許容されると判断。「引用は原著作物をそのまま使用する場合に限定されるという法令上の根拠がない」「要約は著作権者の利益を全文複製より損なわない」とされた。

**現時点の判断：個人利用・ローカル限定・要約独自生成・元記事リンク表示を守れば、日本著作権法上は適法の範囲内と解釈できる。**

遵守事項：
- ローカル環境のみで使用（外部公開しない）
- 元記事へのリンクを必ず表示
- 要約はClaude APIが独自生成したもの（RSSコンテンツの転載ではない）

**⚠️ 残存リスク：** 「AI生成翻訳要約」の著作権上の扱いは法整備途上であり、手順5（リスク正式評価）でより詳細に確認する。

---

## 2. コスト調査

### 2-1. Claude API 料金体系（2026年5月現在）

**出典：** [Anthropic Pricing（公式）](https://www.anthropic.com/pricing)

| モデル | 入力 | 出力 | 用途 |
|---|---|---|---|
| Claude Haiku 4.5 | $1.00/MTok | $5.00/MTok | 翻訳・要約・分類（推奨） |
| Claude Sonnet 4.6 | $3.00/MTok | $15.00/MTok | 品質不足時の代替 |

> **⚠️ 注意：** 上記料金は2026年5月時点。製造着手前に [https://www.anthropic.com/pricing](https://www.anthropic.com/pricing) で最新料金を再確認すること。

### 2-2. 月次コスト試算（Haiku 4.5）

**前提条件：** 1日2回取得 × 30件/回 = 約1,800件/月、入力800トークン/件、出力400トークン/件

| 項目 | 計算 | 金額 |
|---|---|---|
| 月間入力（1,800 × 800tok） | 1.44 MTok × $1.00 | $1.44 |
| 月間出力（1,800 × 400tok） | 0.72 MTok × $5.00 | $3.60 |
| **月額合計（Haiku 4.5）** | | **約$5.04（≒750円）** |
| 参考：Sonnet 4.6の場合 | | 約$15.12（≒2,200円） |

### 2-3. API使用上限の設定

Claude APIのConsoleからWorkspaceごとに月次Spend Limitを設定可能。上限到達時は429エラーが返るため、アプリ側でキャッチして翻訳スキップ+ヘッダーバナー表示を行う。

**設定値：月次$20（試算額の約4倍）。製造着手前にConsoleで設定すること。**

> **⚠️ 未確認事項：** Anthropic ConsoleでのSpend Limit設定手順の詳細は製造着手前に公式ドキュメントで確認する。

### 2-4. レートリミットと処理数の整合性

1日2回・30件のバッチ処理はTier 1のデフォルトレートリミットで十分対応可能。リクエスト間に1秒程度のインターバルを設けることを推奨。

---

## 3. 技術調査

### 3-1. ニュースソースRSSの稼働状況（実機確認済み）

| ソース | 稼働状況 | 確認結果 |
|---|---|---|
| ESPN NBA RSS | ❌ 除外確定 | 利用規約「改変禁止」条項によりv0.1で除外 |
| RealGM | ❌ 除外確定 | RSSフィード（`basketball.realgm.com/rss/wiretap.rss`）が404。実機確認済み |
| Hoops Rumors | ✅ 稼働中 | 実機取得成功。`<category>`タグにチーム名・選手名が含まれることを確認 |
| HoopsHype | ✅ 稼働中 | フェールオーバー用補助ソースとして確認済み |

### 3-2. ✅ 解消済み：代替RSSのチームメタ情報（実機確認済み）

| 確認項目 | 状況 | 確認結果 |
|---|---|---|
| Hoops Rumors RSSのフィールド構成 | ✅ 確認済み | `<title>` / `<description>` / `<category>` / `<link>` / `<pubDate>` を含む |
| `<category>`タグへのチーム名・選手名の含有 | ✅ 確認済み | Spurs・選手名が`<category>`タグに含まれることを確認 |
| Spurs記事のキーワードマッチによる識別 | ✅ 実現可能 | `<category>`タグ内の「Spurs」「San Antonio」等のキーワードマッチで対応可能 |
| RealGM RSSのフィールド構成 | ❌ 確認不要 | RSS 404のため除外確定 |

**チームフィルタF-04の実装方針（確定）：**
`<category>`タグのキーワードマッチ（「Spurs」「San Antonio Spurs」等）を一次フィルタとして使用する。Claude APIによるチーム判定は不要となり、追加コストなしで対応可能。

### 3-3. BALLDONTLIE API（スコア取得）— 動作確認済み

**出典：** [BALLDONTLIE公式](https://www.balldontlie.io/)、[API Docs](https://docs.balldontlie.io/)、[Getting Started](https://www.balldontlie.io/blog/getting-started/)

| 項目 | 内容 | 確認状況 |
|---|---|---|
| 無料ティア登録 | 完了（app.balldontlie.io） | ✅ 確認済み |
| gamesエンドポイント | 最終スコア・クォーター別スコア・勝敗を取得可能 | ✅ 動作確認済み |
| SpursチームIDでの試合データ取得 | 正常取得を確認 | ✅ 動作確認済み |
| statsエンドポイント（個人スタッツ） | **無料ティアでは利用不可（有料ティアのみ）** | ✅ 確認済み・スコープアウト |
| ニュース記事エンドポイント | **なし**（スタッツ・試合データAPIのみ） | ✅ 確認済み |
| 対応リーグ | NBA, NFL, MLB, NHL, EPL等18以上 | — |
| レートリミット | 無料ティア：60リクエスト/分 | — |
| MCP Server | 公式MCPサーバー提供あり | — |

**役割分担（確定）：** ニュース記事→Hoops Rumors RSS、試合スコア（最終・クォーター別・勝敗）→BALLDONTLIE gamesエンドポイント。個人スタッツ（ボックススコア）はスコープ外。

### 3-4. ローカルバッチスケジューリング

朝・夕の2回取得を基本とする。PCスリープ対策として、復帰時に前回取得から一定時間（目安：4時間）以上経過していれば取得を実施する（厳密な時刻指定cronは使用しない）。

---

## 4. コスト総合試算（月次）

| 項目 | 月額コスト | 出典 |
|---|---|---|
| Hoops Rumors RSS | $0 | 無料公開 |
| HoopsHype RSS | $0 | 無料公開（フェールオーバー用） |
| BALLDONTLIE API（gamesエンドポイント） | $0 | 無料ティアで十分 |
| Claude API（Haiku 4.5） | 約$5 | [Anthropic Pricing](https://www.anthropic.com/pricing) |
| **月額合計** | **約$5（≒750円）** | |

**月次上限設定：$20（Anthropic Consoleで設定）**

---

## 5. 総合判断と設計フェーズへの引き継ぎ事項

### 設計着手の判断

✅ **基本設計（手順3）に進んでよい。**

### 基本設計着手前の必須事項（完了済み）

| No. | 事項 | 状況 | 結果 |
|---|---|---|---|
| 1 | RSS実機確認 | ✅ 完了 | Hoops Rumors：`<category>`タグでSpursフィルタ可能。RealGM：RSS 404のため除外 |
| 2 | BALLDONTLIE動作確認 | ✅ 完了 | gamesエンドポイントで試合スコア取得可能。statsエンドポイントは有料ティアのためスコープアウト |

### 設計フェーズで対処すべき事項

| 優先度 | 事項 | 内容 |
|---|---|---|
| 🔴 高 | **Hoops Rumors1本化リスクへのフェールオーバー設計** | RealGM除外によりニュースソースが実質1本に。HoopsHypeへの自動切り替え（フェールオーバー）機構を基本設計に組み込む |
| 🔴 高 | 役割分担の設計 | ニュース記事→Hoops Rumors RSS（主軸）、試合スコア→BALLDONTLIE gamesエンドポイントの2系統を設計に明示する |
| 🔴 高 | 要約独自生成の実装方針 | RSSコンテンツを直接翻訳・表示せず、Claude APIが独自に要約を生成する。元記事URLとクレジット表示を必須とする |
| 🔴 高 | ネタバレ防止のプロンプト設計 | 「試合結果」判定時はスコアを要約に含めないプロンプトを詳細設計（手順4）で設計する |
| 🟡 中 | Claude API月次上限設定 | Console上で$20を設定。製造着手前に実施 |
| 🟡 中 | Claude API料金の再確認 | 製造着手前に [https://www.anthropic.com/pricing](https://www.anthropic.com/pricing) で最新料金を確認しコスト試算を更新する |
| 🟢 低 | 補助RSSソースの追加検討 | The Cold Wire NBA・Hoops Wireの稼働状況を基本設計で実機確認し、追加要否を判断する |
| 🟢 低 | NFL拡張の準備 | BALLDONTLIEはNFL対応済み。フェーズ2への拡張が容易 |

### 手順5（リスク正式評価）で対処すべき事項

| 事項 | 内容 |
|---|---|
| 日本著作権法の詳細確認 | AI生成翻訳要約の著作権上の扱い。個人利用・ローカル限定の条件下での最終評価 |
| 各RSSソースの利用規約の最終確認 | 設計確定後の法的リスクの最終評価 |

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v0.1 | 2026-05-10 | 初版作成（ESPN・NBA.com・Claude APIの調査） |
| v0.2 | 2026-05-10 | ESPNを除外。代替ソース（Hoops Rumors・HoopsHype・RealGM）の利用規約を調査。NBA.com規約を全文精読し再評価。BALLDONTLIE・nba_apiのAPI料金・仕様を調査。コスト総合試算を更新 |
| v0.3 | 2026-05-10 | レビュー指摘（致命3件・改善4件・軽微3件）を反映。①ESPNを除外するに至った経緯をv0.1差分サマリーとして追記、②日本著作権法の調査結果を追記しスコープ外事項（手順5対処）を明示、③代替RSSのチームメタ情報が未確認であることをリスクとして明示、④Claude API料金の参照先を公式URLに修正（`anthropic.com/pricing`）、⑤更新頻度を「1日2回」に統一、⑥「基本設計着手前に完了すべき必須事項」セクションを追加 |
| v0.4 | 2026-05-10 | 再レビュー指摘（新規-1）を反映。§3-4のバッチ方式記述を「朝・夕2回基本・前回取得から4時間経過で実行・cron不使用」に修正。要件定義書v0.5との整合性を確保 |
| v0.5 | 2026-05-10 | RSS実機確認・BALLDONTLIE動作確認の結果を反映。①RealGMをRSS 404のため除外確定、②Hoops Rumors `<category>`タグでSpursフィルタ可能と確認、③BALLDONTLIE gamesエンドポイント動作確認済み・statsエンドポイントはスコープアウト、④ニュースソース構成をHoops Rumors主軸・HoopsHype補助（フェールオーバー）に確定、⑤コスト総合試算からRealGM行を削除、⑥設計引き継ぎ事項に「Hoops Rumors1本化リスクへのフェールオーバー設計」を追加（優先度🔴高）、⑦サマリーの技術リスクを「✅ 解消」に更新。要件定義書v0.6との整合性を確保 |
