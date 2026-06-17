from passlib.context import CryptContext

from config import INIT_USER_PASSWORD, INIT_USERNAME

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_user(db) -> None:
    """startupイベント時に呼び出す。usersテーブルが空の場合のみ初回ユーザーを作成（冪等性あり）。"""
    if db.count_users() > 0:
        return
    hashed = pwd_context.hash(INIT_USER_PASSWORD)
    db.create_user(username=INIT_USERNAME, hashed_password=hashed)


def authenticate_user(username: str, password: str, db) -> bool:
    """ユーザー名とパスワードを検証する"""
    user = db.get_user(username)
    if not user:
        return False
    return pwd_context.verify(password, user["hashed_password"])
