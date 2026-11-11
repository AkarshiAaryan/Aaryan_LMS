import os
import tempfile
import pytest

# Point to temporary SQLite test db before any app modules are loaded
test_db_path = os.path.join(tempfile.gettempdir(), "test_guardslm.db")
if os.path.exists(test_db_path):
    try:
        os.remove(test_db_path)
    except Exception:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

from fastapi.testclient import TestClient
from ..database import Base, get_db, engine, SessionLocal
from ..main import app
from ..seed import seed_database
from ..auth import create_access_token
from ..models import User


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    def _get_headers(username: str, role: str = "student", user_id: int = 1):
        token = create_access_token(data={"sub": username, "role": role, "id": user_id})
        return {"Authorization": f"Bearer {token}"}
    return _get_headers
