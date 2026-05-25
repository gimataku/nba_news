"""T-05: Claude API正常 / T-06: カテゴリ境界 / T-07: ネタバレ防止 / T-09: API上限管理"""
import json
import re
from unittest.mock import MagicMock

import anthropic
import pytest

import processor.claude_client as cc
from db import crud


def _make_mock_response(payload: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.content[0].text = json.dumps(payload)
    return mock_resp


def _make_rate_limit_error() -> anthropic.RateLimitError:
    mock_http = MagicMock()
    mock_http.status_code = 429
    mock_http.headers = {}
    mock_http.request = MagicMock()
    return anthropic.RateLimitError(
        message="Rate limit exceeded",
        response=mock_http,
        body=None,
    )


# ── T-05 ──────────────────────────────────────────────────────────────────────

def test_t05_normal_response(mocker):
    """T-05: 翻訳・要約・分類が正常なJSON形式で返ること"""
    mocker.patch("processor.claude_client.time.sleep")
    mocker.patch(
        "processor.claude_client.anthropic_client.messages.create",
        return_value=_make_mock_response({
            "title_ja": "スパーズが新ガードと契約",
            "summary_ja": "サンアントニオ・スパーズは新しいガードを獲得した。",
            "category": "contract",
            "has_score": False,
        }),
    )

    result = cc.process_article("Spurs sign new guard", "San Antonio Spurs...")

    assert result is not None
    assert isinstance(result["title_ja"], str)
    assert isinstance(result["summary_ja"], str)
    assert result["category"] in ("trade", "contract", "game", "column")
    assert isinstance(result["has_score"], bool)
    assert result["category"] == "contract"
    assert result["has_score"] is False


# ── T-06 ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("category,should_be_none", [
    ("trade",         False),
    ("contract",      False),
    ("game",          False),
    ("column",        False),
    ("invalid_value", True),
])
def test_t06_category_boundary(mocker, category, should_be_none):
    """T-06: カテゴリ分類の境界条件"""
    mocker.patch("processor.claude_client.time.sleep")
    mocker.patch(
        "processor.claude_client.anthropic_client.messages.create",
        return_value=_make_mock_response({
            "title_ja": "テスト記事",
            "summary_ja": "テスト要約。",
            "category": category,
            "has_score": False,
        }),
    )

    result = cc.process_article("Test article", "Test description")

    if should_be_none:
        assert result is None
    else:
        assert result is not None
        assert result["category"] == category


# ── T-07 ──────────────────────────────────────────────────────────────────────

def test_t07_spoiler_prevention(mocker):
    """T-07: gameカテゴリ時、summary_jaにスコアパターンが含まれないこと"""
    mocker.patch("processor.claude_client.time.sleep")
    mocker.patch(
        "processor.claude_client.anthropic_client.messages.create",
        return_value=_make_mock_response({
            "title_ja": "スパーズが勝利",
            "summary_ja": "スパーズは本日の試合で素晴らしいパフォーマンスを見せた。",
            "category": "game",
            "has_score": True,
        }),
    )

    result = cc.process_article(
        "Spurs win tonight",
        "San Antonio Spurs defeated the Lakers 110-105.",
    )

    assert result is not None
    assert result["category"] == "game"
    assert not re.search(r"\d+-\d+", result["summary_ja"]), (
        f"summary_ja にスコアパターンが含まれている: {result['summary_ja']}"
    )
    assert "勝" not in result["summary_ja"]
    assert "敗" not in result["summary_ja"]


# ── T-09 ──────────────────────────────────────────────────────────────────────

def test_t09_rate_limit_sets_flag(mocker):
    """T-09 ケース1: 429エラー → Noneを返し api_limit_exceeded="true" になること"""
    mocker.patch("processor.claude_client.time.sleep")
    mocker.patch(
        "processor.claude_client.anthropic_client.messages.create",
        side_effect=_make_rate_limit_error(),
    )

    result = cc.process_article("Spurs news", "Some content")

    assert result is None
    assert crud.get_setting("api_limit_exceeded") == "true"


def test_t09_monthly_reset(mocker):
    """T-09 ケース2: 月次リセット → api_limit_exceeded が "false" にリセットされること"""
    crud.set_setting("api_limit_exceeded", "true")
    crud.set_setting("api_reset_month", "2026-04")

    mocker.patch("scheduler.fetch_rss", return_value=([], "", True))

    from scheduler import run_batch
    run_batch()

    assert crud.get_setting("api_limit_exceeded") == "false"
