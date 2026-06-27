"""T-P2-01: ログイン・トークン発行 / T-P2-02-5: loginはJWT不要 / T-P2-03: init_user冪等性"""
from config import INIT_USERNAME, INIT_USER_PASSWORD
from db import crud


def _init_user():
    """テスト用ユーザーをDBに作成する"""
    from auth.users import init_user
    init_user(crud)


# ── T-P2-01 ──────────────────────────────────────────────────────────────────

def test_tc_p2_01_1_login_success(raw_api_client):
    """TC-P2-01-1: 正しいユーザー名・パスワード → HTTP 200 / access_token / token_type=bearer"""
    _init_user()

    resp = raw_api_client.post(
        "/api/auth/login",
        json={"username": INIT_USERNAME, "password": INIT_USER_PASSWORD},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 0


def test_tc_p2_01_2_login_wrong_password(raw_api_client):
    """TC-P2-01-2: 正しいユーザー名・誤ったパスワード → HTTP 401"""
    _init_user()

    resp = raw_api_client.post(
        "/api/auth/login",
        json={"username": INIT_USERNAME, "password": "wrongpass_XYZ"},
    )

    assert resp.status_code == 401


def test_tc_p2_01_3_login_unknown_user(raw_api_client):
    """TC-P2-01-3: 存在しないユーザー名 → HTTP 401"""
    resp = raw_api_client.post(
        "/api/auth/login",
        json={"username": "nobody_unknown_xyz", "password": INIT_USER_PASSWORD},
    )

    assert resp.status_code == 401


# ── T-P2-02-5 ────────────────────────────────────────────────────────────────

def test_tc_p2_02_5_login_no_jwt_header(raw_api_client):
    """TC-P2-02-5: JWTヘッダーなし・正しいユーザー名&パスワード → /api/auth/login は HTTP 200"""
    _init_user()

    resp = raw_api_client.post(
        "/api/auth/login",
        json={"username": INIT_USERNAME, "password": INIT_USER_PASSWORD},
        # Authorizationヘッダーを意図的に送らない
    )

    assert resp.status_code == 200
    assert "access_token" in resp.json()


# ── T-P2-03 ──────────────────────────────────────────────────────────────────

def test_tc_p2_03_1_init_user_creates_first_user():
    """TC-P2-03-1: usersテーブルが空 → init_user() で1件作成される"""
    assert crud.count_users() == 0

    _init_user()

    assert crud.count_users() == 1


def test_tc_p2_03_2_init_user_idempotent():
    """TC-P2-03-2: 既存ユーザーあり → init_user() を再実行しても重複しない"""
    _init_user()
    assert crud.count_users() == 1

    _init_user()  # 2回目

    assert crud.count_users() == 1
