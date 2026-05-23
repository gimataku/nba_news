# リスク調査レポート（再調査版）

- **バージョン**: v0.2
- **ステータス**: 完了
- **作成日**: 2026-05-10
- **対象**: NBAニュース翻訳アプリ（個人利用）
- **前版からの変更**: ESPNのRSS/APIを除外。代替ニュースソース・NBA.com規約・サイトAPI料金を再調査。

---

## サマリー

| 区分 | 判定 | 概要 |
|---|---|---|
| 法的リスク | ✅ 改善 | Hoops Rumors・HoopsHype等の代替ソースはESPNより規約が緩やか。要約独自生成方式で対応可能 |
| コストリスク | ✅ 低リスク | ニュースデータAPIはすべて無料または低コストで利用可能。Claude APIは月額$5程度 |
| 技術リスク | ⚠️ 注意点あり | BALLDONTLIEはスタッツAPIであり「ニュース記事」は提供なし。ニュース取得はRSSと明確に役割分担が必要 |

**設計着手の判断：進めてよい**
ESPNを除外することで法的リスクが改善された。ニュース系ソース（RSS）とスタッツ系API（BALLDONTLIE）の役割分担を設計で明確にすること。

---

## 1. ESPNを除外する理由（確定）

| 理由 | 内容 | 出典 |
|---|---|---|
| 利用規約「改変禁止」 | "You may not modify any content provided in the feed, including but not limited to story headlines, story summaries, or URLs." | [ESPN RSS Index](https://www.espn.com/espn/news/story?id=3437834) |
| チーム名タグなし | RSSフィードには標準的なチーム名タグが含まれず、フィルタ実装が困難 | 前回調査 |

---

## 2. 代替ニュースソースの提案と利用規約調査

### 2-1. 代替ソース一覧

| ソース | RSS URL | 特徴 | 規約リスク |
|---|---|---|---|
| **Hoops Rumors** | `hoopsrumors.com/feed` | トレード・FA特化。週50件以上の記事量 | ✅ 低（後述） |
| **HoopsHype** | `hoopshype.com/feed` | USA Today Sports傘下。契約・サラリー情報に強い | ⚠️ 中（後述） |
| **RealGM** | `basketball.realgm.com/rss/wiretap.rss` | ニュース・スタッツ網羅。記事に出典明記 | ✅ 低 |
| **The Cold Wire NBA** | `thecoldwire.com/sports/nba/feed` | 一般NBAニュース | ✅ 低 |
| **Hoops Wire** | `hoopswire.com/feed` | トレード・ドラフト情報 | ✅ 低 |

---

### 2-2. Hoops Rumors の利用規約

**調査結果：**

Hoops Rumorsは独立したブログ形式のサイト（Tim Dierkes氏が2012年に創設）であり、WordPressベースで運営されている。公開されている規約はコメントポリシーとプライバシーポリシーのみで、RSS利用に関する明示的な禁止条項は確認できなかった。

- プライバシーポリシー：Google広告のCookieポリシーのみ記載。RSS規制なし。
- コメントポリシー：コメント投稿に関するルールのみ。

**出典：** [Hoops Rumors About Page](https://www.hoopsrumors.com/2011/11/about-hoops-rumors.html)、[Privacy Policy](https://www.hoopsrumors.com/2012/01/hoopsrumorscom-privacy-policy.html)

**判定：✅ RSS個人利用は問題なし**

明示的な禁止規定がなく、RSSを公開提供している。個人利用・非公開アプリでの利用は許容範囲内と判断できる。ただし以下を遵守する：
- 元記事へのリンクを必ず表示
- Hoops Rumorsのクレジット表示
- 商業的利用は不可

---

### 2-3. HoopsHype の利用規約

**調査結果：**

HoopsHypeは2012年にUSA Today Sports Media Group（Gannett Co.傘下）に買収されており、USA Today / Gannettの利用規約が適用される。

サブスクリプション利用規約はあるが、RSSの個人利用に関する明示的な禁止条項は確認できなかった。ただし大手メディア傘下であるため、コンテンツの再利用・翻訳に関して今後規約が厳格化される可能性がある。

**出典：** [Wikipedia - HoopsHype](https://en.wikipedia.org/wiki/HoopsHype)、[HoopsHype Help Center](https://help.hoopshype.com/)

**判定：⚠️ 利用可能だが注意が必要**

RSSの個人利用自体に明示的な禁止はないが、Gannett傘下の大手メディアであるため、より規約が厳格な可能性がある。補助的なソースとして使用し、主軸はHoops Rumorsに置くことを推奨。

---

### 2-4. 推奨するニュースソース構成

| 役割 | ソース | 取得内容 |
|---|---|---|
| **主軸（トレード・契約・FA）** | Hoops Rumors RSS | トレード噂・サイン情報・FA動向 |
| **補助（一般ニュース・コラム）** | RealGM RSS | ニュース全般・スタッツ付き記事 |
| **補助（契約詳細）** | HoopsHype RSS | 契約情報・サラリー関連 |

チームフィルタ（Spurs関連）：RSSに含まれる見出し・本文から「Spurs」「San Antonio」等のキーワード検索 + Claude APIによるチーム判定を組み合わせる。

---

## 3. NBA.com 利用規約の再調査

**調査結果：** [NBA.com Terms of Use](https://www.nba.com/termsofuse) を全文精読（2023年2月20日最終更新）。

### 3-1. 利用制限（重要条項）

NBA.comのコンテンツは個人的な娯楽・情報・教育・通信目的でのみ維持されており、個人の非商業的利用に限り単一コンピュータへのダウンロードが許可されている。ただし、書面による許可なしに、配布・複製・再公開・アップロード・表示・改変・再送信・再利用・再投稿・他のウェブサイトやSNSでの利用は禁止されている。

### 3-2. モジュールコンテンツ（RSS）に関する条項

NBA.comはRSSフィードを含むモジュールコンテンツを提供することがあり、利用者はこれを利用規約および追加ルールに従って責任を持って利用することが求められる。NBA.comのブランド表示を隠したり、所有権を主張したり、コンテンツを抜粋・編集することは禁止されている（Operatorが明示的に許可した場合を除く）。

### 3-3. NBAスタッツに関する特別条項

NBA.comのスタッツについては個人の非商業的目的での利用のみ許可されており、NBA.comへの出典表示が必須。ギャンブル・ファンタジースポーツ・スポーツベッティングへの利用は禁止。

**出典：** [NBA.com Terms of Use §1, §7, §9](https://www.nba.com/termsofuse)

### 3-4. NBA.com に関する判定

| 項目 | 判定 | 理由 |
|---|---|---|
| NBA.com RSSの個人利用 | ⚠️ 要注意 | 「抜粋・編集禁止」条項が翻訳・要約と抵触する可能性あり |
| NBA.comスタッツの利用 | ✅ 条件付き可 | 個人・非商業・NBA.com出典表示の3条件を満たせば利用可能 |
| NBA.comを主要ニュースソースにすること | ❌ 非推奨 | 「改変禁止」条項がESPNと同様の問題を生じる |

**結論：NBA.comはニュース記事の主要ソースとしては使用しない。スタッツデータ（試合結果・スコア）の補足参照に限定し、出典を明示する。**

---

## 4. 利用サイトのAPI料金調査

### 4-1. ニュース系ソース（RSS）

| ソース | API/RSS料金 | 備考 |
|---|---|---|
| Hoops Rumors | **無料** | RSSは無償公開。有料プランはコメント機能等（$34.99/年）で、RSS利用とは無関係 |
| HoopsHype | **無料** | RSSは無償公開 |
| RealGM | **無料** | RSSは無償公開 |
| The Cold Wire NBA | **無料** | RSSは無償公開 |
| NBA.com | **無料（条件付き）** | モジュールコンテンツは無償だが利用規約の遵守が必要 |

**ニュース取得コスト：$0/月**

---

### 4-2. スタッツ系API（試合結果・スコア取得用）

ニュース記事の取得はRSSで行うが、試合結果（スコア・ボックススコア）は別途スタッツAPIから取得することでネタバレ防止機能と連携させる設計が有効。

#### BALLDONTLIE API

| 項目 | 内容 | 出典 |
|---|---|---|
| 無料ティア | あり。基本エンドポイントへのアクセス（スコア・スタッツ・ロスター等）が無料 | [BALLDONTLIE公式](https://www.balldontlie.io/)、[Getting Started](https://www.balldontlie.io/blog/getting-started/) |
| 対応リーグ | NBA, NFL, MLB, NHL, EPL, WNBA, NCAAF, NCAAB, MMA等 | [BALLDONTLIE公式](https://www.balldontlie.io/) |
| NFL対応 | ✅ あり（フェーズ2への拡張に有利） | [BALLDONTLIE公式](https://www.balldontlie.io/) |
| ニュース記事エンドポイント | **なし** | 調査結果（ドキュメント確認済み） |
| 提供データ | スコア・スタッツ・試合データ・ボックススコア・スタンディング・選手情報 | [API Docs](https://docs.balldontlie.io/) |
| 料金 | 無料ティアあり。上位ティアはスポーツ別課金（詳細は要確認） | [PulseMCP](https://www.pulsemcp.com/servers/balldontlie) |
| レートリミット | 無料ティア：60リクエスト/分 | [Public APIs Directory](https://publicapis.io/balldontlie-api) |
| MCP Server | 公式MCPサーバー提供あり（Claude連携が容易） | [GitHub](https://github.com/balldontlie-api/mcp) |

**⚠️ 重要：BALLDONTLIEはスタッツ・試合データAPIであり、ニュース記事は提供していない。**

ニュース記事はRSSから取得し、試合結果・スタッツはBALLDONTLIEから取得するという明確な役割分担が必要。

#### nba_api（Python非公式クライアント）

| 項目 | 内容 | 出典 |
|---|---|---|
| 料金 | **完全無料**（NBA.comの非公式エンドポイントを利用） | [GitHub - swar/nba_api](https://github.com/swar/nba_api) |
| 提供データ | 選手スタッツ・試合データ・ライブスコア等 | [GitHub](https://github.com/swar/nba_api) |
| 法的リスク | NBA.comの利用規約に準拠する必要あり。非公式のため仕様変更・廃止リスクあり | [GitHub](https://github.com/swar/nba_api) |
| 推奨度 | △（非公式のため安定性に懸念。BALLDONTLIEを優先） | — |

---

### 4-3. Claude API（翻訳・要約・カテゴリ分類）

（前回調査から変更なし）

| モデル | 入力 | 出力 | 推奨用途 | 出典 |
|---|---|---|---|---|
| Claude Haiku 4.5 | $1.00/MTok | $5.00/MTok | 翻訳・要約・分類に最適 | [Anthropic Pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| Claude Sonnet 4.6 | $3.00/MTok | $15.00/MTok | 品質不足時の代替 | [Anthropic Pricing](https://platform.claude.com/docs/en/about-claude/pricing) |

**月次コスト試算（Haiku 4.5）：約$5.04（≒750円）**

詳細計算は前版レポート（v0.1）を参照。

---

## 5. コスト総合試算（月次）

| 項目 | 月額コスト | 備考 |
|---|---|---|
| Hoops Rumors RSS | $0 | 無料 |
| HoopsHype RSS | $0 | 無料 |
| RealGM RSS | $0 | 無料 |
| BALLDONTLIE API | $0 | 無料ティアで十分 |
| Claude API（Haiku 4.5） | 約$5 | 月1,800件の翻訳・要約・分類 |
| **月額合計** | **約$5（≒750円）** | Sonnet使用時は約$15 |

**月次上限設定：$20（Console上で設定）**

---

## 6. 総合判断と設計フェーズへの引き継ぎ事項

### 設計着手の判断

✅ **基本設計（手順3）に進んでよい。**

### 設計フェーズで必ず対処すべき事項

| 優先度 | 事項 | 内容 |
|---|---|---|
| 🔴 高 | ニュース取得ソースの確定 | Hoops Rumors（主軸）+ RealGM（補助）を採用。各RSSを実機確認してチーム名タグの有無を確認 |
| 🔴 高 | 役割分担の設計 | ニュース記事 → RSS（Hoops Rumors等）、試合スコア・スタッツ → BALLDONTLIE API の2系統に分離 |
| 🔴 高 | 要約は独自生成 | RSSの本文をそのまま翻訳・表示するのではなく、Claude APIが独自に要約を生成する。元記事URLとクレジット表示を必須とする |
| 🟡 中 | NBA.comの利用を限定 | NBA.comはスタッツの補足参照のみ。ニュース取得には使用しない |
| 🟡 中 | BALLDONTLIE APIキー取得 | 無料ティア登録（app.balldontlie.io）。製造前に動作確認 |
| 🟡 中 | Claude API月次上限設定 | Console上で$20を上限に設定。製造着手前に実施 |
| 🟢 低 | Spurs専用ニュース補強 | 上記ソースでSpurs記事量が不足する場合、San Antonio Express-News等のRSS追加を検討 |
| 🟢 低 | NFL拡張の準備 | BALLDONTLIEはNFLにも対応しており、フェーズ2への拡張が容易 |

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v0.1 | 2026-05-10 | 初版作成 |
| v0.2 | 2026-05-10 | ESPNを除外。代替ソース（Hoops Rumors・HoopsHype・RealGM）の利用規約を調査。NBA.com規約を全文精読し再評価。BALLDONTLIEおよびnba_apiのAPI料金・仕様を調査。コスト総合試算を更新 |
