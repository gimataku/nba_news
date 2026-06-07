# 実機確認手順書（フェーズ2 リスク事前調査）

- **バージョン**: v0.1
- **作成日**: 2026-06-06
- **参照**: リスク調査書 フェーズ2 v0.5（`risk_report_p2_v0.5.md`）§3-1・§3-2
- **目的**: 手順2（リスク事前調査）のfix条件となる実機確認3件を実施する

---

## 確認項目の全体像

| No. | 確認内容 | 影響 | 完了 |
|---|---|---|---|
| 1 | BALLDONTLIE games（試合日程・会場） | C-05スコープ確定 | ☐ |
| 2 | BALLDONTLIE standings（順位） | C-04スコープ確定 | ☐ |
| 3 | 追加RSSソースの実機確認 | C-05速報ニュース採用ソース確定 | ☐ |

**所要時間目安：約20分**

---

## 事前準備

### 1. PowerShellを管理者権限で開く

```powershell
Windowsキー → 「PowerShell」と入力 → 「管理者として実行」
```

### 2. APIキーを環境変数にセット

```powershell
$env:BALLDONTLIE_API_KEY = "（.envファイルに記載のAPIキーをここに貼り付け）"
```

確認：

```powershell
echo $env:BALLDONTLIE_API_KEY
# APIキーが表示されればOK
```

---

## No.1：BALLDONTLIE games（C-05スコープ確定）

### 目的

試合日程・会場情報が無料ティアで取得できるかを確認する。

### コマンド

```powershell
curl "https://api.balldontlie.io/v1/games?team_ids[]=27&start_date=2026-06-06&end_date=2026-06-30" `
  -H "Authorization: Bearer $env:BALLDONTLIE_API_KEY"
```

### 正常なレスポンス例

```json
{
  "data": [
    {
      "id": 21713533,
      "date": "2026-06-07T00:00:00.000Z",
      "status": "scheduled",
      "home_team": {
        "id": 27,
        "abbreviation": "SAS",
        "city": "San Antonio",
        "name": "Spurs"
      },
      "visitor_team": {
        "id": 21,
        "abbreviation": "OKC",
        "city": "Oklahoma City",
        "name": "Thunder"
      },
      "home_team_score": 0,
      "visitor_team_score": 0,
      "period": 0
    }
  ]
}
```

### 確認項目と記録欄

| 確認項目 | 確認内容 | 結果 |
|---|---|---|
| 1-A | HTTPステータスが200か（認証エラー401・有料制限402でないか） | ☐ OK　/ ☐ NG |
| 1-B | `data`配列に試合データが含まれるか | ☐ OK　/ ☐ NG |
| 1-C | `date`フィールドに日時が含まれるか | ☐ OK　/ ☐ NG |
| 1-D | `home_team.city`または会場情報が含まれるか | ☐ OK　/ ☐ NG |
| 1-E | オフシーズン期間（2026年6月）でも404にならないか | ☐ OK　/ ☐ NG |

### 判断基準

| 結果 | 判断 |
|---|---|
| 1-A〜1-Eが全てOK | ✅ **C-05スコープ内**（BALLDONTLIE gamesエンドポイントを採用） |
| 1-Aが401または402 | ❌ **C-05スコープアウト**（有料ティアのみ） |
| 1-Bが空配列（`"data": []`） | ⚠️ オフシーズンのため試合なし。シーズン中の日付で再実行 |
| 1-D会場情報がない | ⚠️ 会場なしで許容するか判断が必要（基本設計で対処） |

### NG時の代替コマンド（オフシーズン確認用）

```powershell
# 直近のシーズン中の試合を確認
curl "https://api.balldontlie.io/v1/games?team_ids[]=27&start_date=2026-04-01&end_date=2026-04-30" `
  -H "Authorization: Bearer $env:BALLDONTLIE_API_KEY"
```

---

## No.2：BALLDONTLIE standings（C-04スコープ確定）

### 目的

順位情報（勝数・敗数・勝率・GB・カンファレンス区別）が無料ティアで取得できるかを確認する。

### コマンド

```powershell
curl "https://api.balldontlie.io/v1/standings?season=2025" `
  -H "Authorization: Bearer $env:BALLDONTLIE_API_KEY"
```

### 正常なレスポンス例

```json
{
  "data": [
    {
      "team": {
        "id": 27,
        "abbreviation": "SAS",
        "city": "San Antonio",
        "name": "Spurs",
        "conference": "West"
      },
      "wins": 45,
      "losses": 37,
      "win_pct": 0.549,
      "games_behind": 2.0,
      "season": 2025
    }
  ]
}
```

### 確認項目と記録欄

| 確認項目 | 確認内容 | 結果 |
|---|---|---|
| 2-A | HTTPステータスが200か（401・402・404でないか） | ☐ OK　/ ☐ NG |
| 2-B | `data`配列に順位データが含まれるか | ☐ OK　/ ☐ NG |
| 2-C | `wins`・`losses`・`win_pct`フィールドがあるか | ☐ OK　/ ☐ NG |
| 2-D | `games_behind`（GB）フィールドがあるか | ☐ OK　/ ☐ NG |
| 2-E | カンファレンス区別（`conference`フィールド等）があるか | ☐ OK　/ ☐ NG |

### 判断基準

| 結果 | 判断 |
|---|---|
| 2-A〜2-Eが全てOK | ✅ **C-04スコープ内**（BALLDONTLIE standingsエンドポイントを採用） |
| 2-Aが401または402 | ❌ **C-04スコープアウト**（有料ティアのみ） |
| 2-Aが404 | ❌ **C-04スコープアウト**（standingsエンドポイントが存在しない） |
| 2-Eがない（カンファレンス区別なし） | ⚠️ East/West表示なしで許容するか判断が必要（基本設計で対処） |

---

## No.3：追加RSSソースの実機確認（C-05速報ニュース採用ソース確定）

### 目的

試合速報を扱うRSSソースが利用可能かを確認する。C-05の2系統表示（APIデータ＋速報ニュース）の速報側ソースを特定する。

### コマンド

以下を1行ずつ実行し、StatusCodeを記録する。

```powershell
# The Athletic NBA RSS
try {
    $r = Invoke-WebRequest "https://theathletic.com/nba/feed/" -TimeoutSec 10
    Write-Host "The Athletic: $($r.StatusCode)"
} catch { Write-Host "The Athletic: ERROR - $($_.Exception.Message)" }

# Bleacher Report NBA
try {
    $r = Invoke-WebRequest "https://bleacherreport.com/nba.rss" -TimeoutSec 10
    Write-Host "Bleacher Report: $($r.StatusCode)"
} catch { Write-Host "Bleacher Report: ERROR - $($_.Exception.Message)" }

# Basketball Reference
try {
    $r = Invoke-WebRequest "https://www.basketball-reference.com/friv/rss.fcgi" -TimeoutSec 10
    Write-Host "Basketball Reference: $($r.StatusCode)"
} catch { Write-Host "Basketball Reference: ERROR - $($_.Exception.Message)" }
```

### 確認項目と記録欄

| ソース | StatusCode | categoryタグあり | 試合速報を扱うか | 採用可否 |
|---|---|---|---|---|
| The Athletic | 　　　 | ☐ あり / ☐ なし | ☐ あり / ☐ なし | ☐ 採用 / ☐ 不採用 |
| Bleacher Report | 　　　 | ☐ あり / ☐ なし | ☐ あり / ☐ なし | ☐ 採用 / ☐ 不採用 |
| Basketball Reference | 　　　 | ☐ あり / ☐ なし | ☐ あり / ☐ なし | ☐ 採用 / ☐ 不採用 |

### categoryタグの確認方法

StatusCode 200のソースについて、RSSのXMLを確認する。

```powershell
# 例：The Athleticのcategoryタグを確認
$xml = [xml](Invoke-WebRequest "https://theathletic.com/nba/feed/").Content
$xml.rss.channel.item | Select-Object title, category | Select-Object -First 5
```

categoryタグに `"San Antonio Spurs"` や `"NBA"` が含まれるか確認する。

### 判断基準

| 結果 | 判断 |
|---|---|
| StatusCode 200・試合速報あり・categoryタグあり | ✅ **採用候補**（フェーズ1のフェールオーバー構成に追加） |
| StatusCode 200・試合速報なし | ❌ 不採用（速報ソースとして不適切） |
| StatusCode 403・404・タイムアウト | ❌ 不採用（アクセス不可） |

> **注記：** 採用候補が0件の場合、C-05の速報ニュース表示はスコープアウトとなる。C-05はBALLDONTLIE APIデータのみの表示に変更する。

---

## 確認完了後の記録

全件完了後、以下に結果を記入してください。

### No.1 games 最終判断

```
判断：✅ C-05スコープ内 / ❌ C-05スコープアウト
理由：
```

### No.2 standings 最終判断

```
判断：✅ C-04スコープ内 / ❌ C-04スコープアウト
理由：
```

### No.3 RSS 採用ソース

```
採用ソース：（ソース名を記入。なければ「なし」）
速報ニュースのスコープ：✅ スコープ内 / ❌ スコープアウト
理由：
```

---

## 完了後の次のアクション

確認結果をClaude（ベテランエンジニア役）に報告してください。
結果をもとにリスク調査書をfixし、手順3「基本設計」に進みます。
