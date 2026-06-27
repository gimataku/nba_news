"""T-P2-04: Levenshtein重複排除（is_duplicateフラグ）"""
import pytest

from processor.dedup import is_duplicate


def _mock_db(mocker, titles: list[str]):
    db = mocker.MagicMock()
    db.get_recent_titles.return_value = titles
    return db


# ── TC-P2-04-1: 完全一致 ─────────────────────────────────────────────────────

def test_tc_p2_04_1_exact_match(mocker):
    """TC-P2-04-1: 完全一致 → True（重複）"""
    db = _mock_db(mocker, ["Spurs sign veteran guard"])

    result = is_duplicate("Spurs sign veteran guard", db)

    assert result is True


# ── TC-P2-04-2: 1文字差（類似度≒98%）───────────────────────────────────────

def test_tc_p2_04_2_near_match(mocker):
    """TC-P2-04-2: 1文字差（類似度≒98%） → True（重複）"""
    db = _mock_db(mocker, ["Spurs sign veteran guard"])

    result = is_duplicate("Spurs signs veteran guard", db)

    assert result is True


# ── TC-P2-04-3: 無関係タイトル ───────────────────────────────────────────────

def test_tc_p2_04_3_unrelated(mocker):
    """TC-P2-04-3: 無関係タイトル → False（類似度低）"""
    db = _mock_db(mocker, ["Spurs sign veteran guard"])

    result = is_duplicate("Lakers trade star player", db)

    assert result is False


# ── TC-P2-04-4: 無関係タイトル（別パターン） ──────────────────────────────────

def test_tc_p2_04_4_unrelated_injury(mocker):
    """TC-P2-04-4: 無関係タイトル → False"""
    db = _mock_db(mocker, ["Lakers sign new center"])

    result = is_duplicate("Spurs Injury Report: Wembanyama", db)

    assert result is False


# ── TC-P2-04-5: DB空（比較対象なし） ─────────────────────────────────────────

def test_tc_p2_04_5_empty_db(mocker):
    """TC-P2-04-5: 直近7日の記事なし（DB空） → False（比較対象なし）"""
    db = _mock_db(mocker, [])

    result = is_duplicate("Spurs sign veteran guard", db)

    assert result is False


# ── TC-P2-04-6: 空文字タイトル ────────────────────────────────────────────────

def test_tc_p2_04_6_empty_title(mocker):
    """TC-P2-04-6: 空文字タイトル → False（空タイトルは重複判定しない）"""
    db = _mock_db(mocker, ["Spurs sign veteran guard"])

    result = is_duplicate("", db)

    assert result is False
