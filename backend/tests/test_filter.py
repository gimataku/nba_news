"""T-04: Spursフィルタ / T-15: フェールオーバー時Spursフィルタ"""
from processor.filter import is_spurs_related


class _Tag:
    def __init__(self, term: str):
        self.term = term


class _Entry:
    def __init__(self, tags=None, title="", summary="", description=""):
        self.tags = [_Tag(t) for t in (tags or [])]
        self._data = {"title": title, "summary": summary, "description": description}

    def get(self, key, default=""):
        return self._data.get(key, default)


# ── T-04 ──────────────────────────────────────────────────────────────────────

def test_t04_category_spurs():
    """T-04 ケース1: categoryタグに「Spurs」あり → True"""
    entry = _Entry(tags=["Spurs"])
    assert is_spurs_related(entry) is True


def test_t04_category_san_antonio_spurs():
    """T-04 ケース2: categoryタグに「San Antonio Spurs」あり → True"""
    entry = _Entry(tags=["San Antonio Spurs"])
    assert is_spurs_related(entry) is True


def test_t04_fallback_title_description():
    """T-04 ケース3: categoryタグなし、title/descriptionにSpursあり → True"""
    entry = _Entry(title="San Antonio Spurs beat Lakers", summary="Spurs won the game.")
    assert is_spurs_related(entry) is True


def test_t04_no_match():
    """T-04 ケース4: 全てなし → False"""
    entry = _Entry(title="Lakers beat Celtics", summary="Great game in Boston.", description="Exciting matchup tonight.")
    assert is_spurs_related(entry) is False


# ── T-15 ──────────────────────────────────────────────────────────────────────

def test_t15_hoops_wire_format():
    """T-15 ケース1: Hoops Wire形式 category=["Spurs"] → True"""
    entry = _Entry(tags=["Spurs"])
    assert is_spurs_related(entry) is True


def test_t15_cold_wire_format():
    """T-15 ケース2: The Cold Wire形式 category=["San Antonio Spurs Rumors And News (Updated Daily)"] → True"""
    entry = _Entry(tags=["San Antonio Spurs Rumors And News (Updated Daily)"])
    assert is_spurs_related(entry) is True


def test_t15_no_category_fallback():
    """T-15 ケース3: categoryなし、title/descriptionにSpursあり → True"""
    entry = _Entry(description="Wembanyama continues to impress in San Antonio.")
    assert is_spurs_related(entry) is True
