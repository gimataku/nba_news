# リスク調査レポート

- **バージョン**: v0.3
- **ステータス**: 完了（一部引き継ぎ事項あり）
- **作成日**: 2026-05-10
- **更新日**: 2026-05-10
- **対象**: NBAニュース翻訳アプリ（個人利用）
- **参照**: プロジェクト計画書 v0.2（`project_plan_v0.2.md`）、要件定義書 v0.4（`requirements_v0.4.md`）

---

## サマリー

| 区分 | 判定 | 概要 |
|---|---|---|
| 法的リスク | ✅ 条件付き適法 | Hoops Rumors・RealGM等の代替ソースはESPNより規約が緩やか。要約独自生成方式で対応可能。日本著作権法の詳細は手順5（リスク正式評価）で対処 |
| コストリスク | ✅ 低リスク | ニュースRSS・BALLDONTLIE APIはすべて無料。Claude APIは月額$5程度（Haiku 4.5使用） |
| 技術リスク | ⚠️ 残存リスクあり | 代替RSSソースのチームメタ情報（チーム名タグ等）が未実機確認。基本設計着手前に確認が必要 |

**設計着手の判断：条件付きで進んでよい**
ESPNを除外することで法的リスクが大幅に改善された。ただし以下の2点を基本設計着手前に完了させること：
1. Hoops Rumors・RealGMのRSSを実機取得し、チームメタ情報の有無を確認する
2. BALLDONTLIE APIキーを取得し、Spurs（チームID）の試合データが取得できることを確認する

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
| **RealGM** | `basketball.realgm.com/rss/wiretap.rss` | ニュース・スタッツ網羅。出典明記 | ✅ 低 |
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

#### 推奨ニュースソース構成

| 役割 | ソース | 主な取得コンテンツ |
|---|---|---|
| **主軸** | Hoops Rumors RSS | トレード噂・サイン・FA動向 |
| **補助** | RealGM RSS | 一般ニュース・スタッツ付き記事 |
| **補助** | HoopsHype RSS | 契約詳細・サラリー情報 |

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

### 3-1. ニュースソースRSSの稼働状況

ESPN NBA RSSはv0.1で除外確定。Hoops Rumors・RealGMは現在も稼働中であることを確認。ただしフィードに含まれるメタ情報の詳細は実機確認が必要（後述）。

### 3-2. ⚠️ 未確認リスク：代替RSSのチームメタ情報

**現状：** Hoops Rumors・RealGMのRSSに、Spurs関連記事を特定できるメタ情報（タグ・カテゴリフィールド等）が含まれるかは未確認。

| 確認項目 | 状況 | リスク影響 |
|---|---|---|
| Hoops Rumors RSSのフィールド構成 | ❌ 未確認 | チームフィルタF-04の実装方式が決まらない |
| RealGM RSSのフィールド構成 | ❌ 未確認 | 同上 |
| Spurs記事を特定できるタグ・カテゴリの有無 | ❌ 未確認 | タグなし → Claude API判定に全面依存 |

**タグなしだった場合のコスト影響試算：**

キーワードマッチ（「Spurs」「San Antonio」等）は追加コストなし。Claude API判定を追加する場合は分類APIコールに含まれるため、プロンプト設計次第で追加コストは最小化できる。

**⚠️ アクション：基本設計（手順3）着手前に実機でRSSを取得し、フィールド構成とSpurs記事の識別可否を確認してリスク調査書v0.4に追記すること。**

### 3-3. BALLDONTLIE API（スタッツ取得）

**出典：** [BALLDONTLIE公式](https://www.balldontlie.io/)、[API Docs](https://docs.balldontlie.io/)、[Getting Started](https://www.balldontlie.io/blog/getting-started/)

| 項目 | 内容 |
|---|---|
| 無料ティア | あり。基本エンドポイント（スコア・スタッツ・ロスター等）が無料 |
| ニュース記事エンドポイント | **なし**（スタッツ・試合データAPIのみ） |
| 対応リーグ | NBA, NFL, MLB, NHL, EPL等18以上（NFL対応でフェーズ2拡張に有利） |
| レートリミット | 無料ティア：60リクエスト/分 |
| MCP Server | 公式MCPサーバー提供あり（Claude連携が容易） |

**⚠️ 重要：BALLDONTLIEはスタッツ・試合データAPIであり、ニュース記事は提供しない。**

役割分担：ニュース記事→RSS、試合スコア・スタッツ→BALLDONTLIE API。

### 3-4. ローカルバッチスケジューリング

PCスリープ問題の対処として「起動時・復帰時に前回取得から6時間以上経過していれば取得する」方式を採用する。厳密なcron依存は避ける。

---

## 4. コスト総合試算（月次）

| 項目 | 月額コスト | 出典 |
|---|---|---|
| Hoops Rumors RSS | $0 | 無料公開 |
| HoopsHype RSS | $0 | 無料公開 |
| RealGM RSS | $0 | 無料公開 |
| BALLDONTLIE API | $0 | 無料ティアで十分 |
| Claude API（Haiku 4.5） | 約$5 | [Anthropic Pricing](https://www.anthropic.com/pricing) |
| **月額合計** | **約$5（≒750円）** | |

**月次上限設定：$20（Anthropic Consoleで設定）**

---

## 5. 総合判断と設計フェーズへの引き継ぎ事項

### 設計着手の判断

✅ **条件付きで基本設計（手順3）に進んでよい。**

### 基本設計着手前に完了すべき事項（必須）

| No. | 事項 | 内容 |
|---|---|---|
| 1 | **RSS実機確認** | Hoops Rumors・RealGMのRSSを実機取得し、フィールド構成（title/description/category/tag等）とSpurs記事の識別可否を確認してリスク調査書v0.4に追記する |
| 2 | **BALLDONTLIE動作確認** | 無料ティア登録（app.balldontlie.io）後、SpursのチームIDで試合データが取得できることを確認する |

### 設計フェーズで対処すべき事項

| 優先度 | 事項 | 内容 |
|---|---|---|
| 🔴 高 | 役割分担の設計 | ニュース記事→RSS（Hoops Rumors等）、試合スコア・スタッツ→BALLDONTLIE APIの2系統を設計に明示する |
| 🔴 高 | 要約独自生成の実装方針 | RSSコンテンツを直接翻訳・表示せず、Claude APIが独自に要約を生成する。元記事URLとクレジット表示を必須とする |
| 🔴 高 | ネタバレ防止のプロンプト設計 | 「試合結果」判定時はスコア・スタッツを要約に含めないプロンプトを詳細設計（手順4）で設計する |
| 🟡 中 | Claude API月次上限設定 | Console上で$20を設定。製造着手前に実施 |
| 🟡 中 | NBA.comの利用制限 | ニュース取得には使用しない。スタッツ参照のみ（出典表示必須） |
| 🟡 中 | Claude API料金の再確認 | 製造着手前に [https://www.anthropic.com/pricing](https://www.anthropic.com/pricing) で最新料金を確認し、コスト試算を更新する |
| 🟢 低 | Spurs専用ニュース補強 | 記事量不足の場合、San Antonio Express-News等のRSS追加を検討 |
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
