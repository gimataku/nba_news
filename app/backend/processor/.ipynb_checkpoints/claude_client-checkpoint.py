import json
import logging
import re
import time

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_INTERVAL, CLAUDE_MAX_TOKENS, CLAUDE_MODEL
from db import crud

logger = logging.getLogger(__name__)

# クライアントはモジュールレベルで1度だけ初期化する
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """あなたはNBAニュースの翻訳・要約・分類アシスタントです。
必ずJSON形式のみで回答してください。マークダウンや説明文は不要です。"""

USER_PROMPT_TEMPLATE = """以下のNBAニュース記事を処理してください。

タイトル: {title}
本文抜粋: {description}

以下のJSON形式で回答してください：
{{
  "title_ja": "日本語に翻訳した見出し（原文のニュアンスを保持）",
  "summary_ja": "300〜500字の日本語要約",
  "category": "trade または contract または game または column",
  "has_score": true または false
}}

【分類ルール】
- trade: 移籍・トレード噂・交渉・成立報道（交渉段階も含む）
- contract: サイン・契約延長・FA動向・契約金額の報道
- game: 試合当日〜翌日の速報・スコアを主要情報として含む記事
- column: 試合分析・選手評価・戦術考察・インタビュー等（スコアが引用で含まれる場合も column）

【重要ルール】
- category が "game" の場合、summary_ja にスコア・得点・勝敗を含めないこと
- has_score は本文に具体的な得点数値が含まれる場合のみ true
- JSON 以外の文字列を出力しないこと"""


def process_article(title: str, description: str) -> dict | None:
    """
    Returns: {"title_ja": str, "summary_ja": str, "category": str, "has_score": bool}
    失敗時: None（呼び出し元でスキップ処理）
    """
    try:
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    title=title,
                    description=description[:1000],  # 最大1000文字に制限
                ),
            }],
        )
        raw = response.content[0].text.strip()
        # ```json ... ``` フェンスが含まれる場合は除去
        raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.MULTILINE)
        result = json.loads(raw)

        # バリデーション
        assert result["category"] in ("trade", "contract", "game", "column")
        assert isinstance(result["has_score"], bool)
        return result

    except anthropic.RateLimitError:
        crud.set_setting("api_limit_exceeded", "true")
        return None

    except (json.JSONDecodeError, KeyError, AssertionError):
        logger.warning("Claude response parse error: %s", title)
        return None

    except anthropic.APIError as exc:
        logger.error("Claude API error for '%s': %s", title, exc)
        return None

    finally:
        time.sleep(CLAUDE_INTERVAL)  # 例外発生時もインターバルを確保
