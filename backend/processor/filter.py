from config import SPURS_KEYWORDS


def is_spurs_related(entry) -> bool:
    """
    優先順位1: entry.tags の tag.term にキーワードが含まれるか確認。
    優先順位2: tags が存在しない or マッチなしの場合、
              title + summary + description のテキストにキーワードマッチ。
              feedparser はエントリによって summary / description どちらかのみ
              持つ場合があるため両方を対象にする。
    大文字小文字を区別しない。
    """
    categories = [tag.term.lower() for tag in getattr(entry, "tags", [])]
    for keyword in SPURS_KEYWORDS:
        if any(keyword in cat for cat in categories):
            return True

    text = (
        entry.get("title", "")
        + " " + entry.get("summary", "")
        + " " + entry.get("description", "")
    ).lower()
    return any(keyword in text for keyword in SPURS_KEYWORDS)
