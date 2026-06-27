import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
    override=True,
)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test.db"))

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-dummy-key")
os.environ.setdefault("BALLDONTLIE_API_KEY", "test-dummy-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-purposes-only-32chars")
os.environ.setdefault("USERNAME", "testuser")
os.environ.setdefault("USER_PASSWORD", "testpass123")


@pytest.fixture(scope="session", autouse=True)
def patch_db_session():
    import db.models as models_module
    import db.crud as crud_module

    test_engine = create_engine(
        f"sqlite:///{TEST_DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    original_engine = models_module.engine
    original_models_sl = models_module.SessionLocal
    original_crud_sl = crud_module.SessionLocal

    models_module.engine = test_engine
    models_module.SessionLocal = TestSessionLocal
    crud_module.SessionLocal = TestSessionLocal

    models_module.Base.metadata.create_all(bind=test_engine)

    yield test_engine, TestSessionLocal

    models_module.engine = original_engine
    models_module.SessionLocal = original_models_sl
    crud_module.SessionLocal = original_crud_sl
    test_engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture(autouse=True)
def reset_db(patch_db_session):
    test_engine, TestSessionLocal = patch_db_session
    import db.models as models_module
    from db.models import AppSetting

    models_module.Base.metadata.drop_all(bind=test_engine)
    models_module.Base.metadata.create_all(bind=test_engine)

    with TestSessionLocal() as session:
        for key, value in [
            ("spoiler_guard_enabled",    "true"),
            ("spurs_filter_enabled",     "false"),
            ("last_fetched_at",          ""),
            ("api_limit_exceeded",       "false"),
            ("api_reset_month",          ""),
            ("last_schedule_fetched_at", ""),
        ]:
            session.add(AppSetting(key=key, value=value))
        session.commit()

    yield


@pytest.fixture
def api_client(reset_db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.routes import get_current_user, router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: "testuser"
    with TestClient(app) as client:
        yield client


@pytest.fixture
def raw_api_client(reset_db):
    """JWT認証オーバーライドなしのテストクライアント（認証テスト用）"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    with TestClient(app) as client:
        yield client
