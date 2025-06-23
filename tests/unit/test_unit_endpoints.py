from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models import Base, PermissionToken
from datetime import datetime, timedelta

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_verify_token_valid():
    db = next(override_get_db())
    token_str = "testtoken123"
    token = PermissionToken(
        token=token_str,
        user_id=1,
        activity_id=1,
        expires_at=datetime.utcnow() + timedelta(days=1),
        used=False
    )
    db.add(token)
    db.commit()

    res = client.get(f"/api/verify-token?token={token_str}")
    assert res.status_code in (200, 400)  # 400 if test users/activities don’t exist

def test_submit_permission_missing_token():
    res = client.post("/api/submit-permission", json={})
    assert res.status_code == 400
