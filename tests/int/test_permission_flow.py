import os
import shutil
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app
from api.models import Base, User, Activity, PermissionToken, ActivityPermission
from api.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

# -- Set up test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_flow.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# -- Dependency override
def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def seed_test_data():
    db = next(override_db())

    # User and Activity
    user = User(id=1, first_name="Test", last_name="User", guardian_name="Test Guardian", guardian_email="guardian@example.com")
    activity = Activity(id=1, activity_name="Campout", description="3-day camp", date_start=datetime(2025, 7, 1), date_end=datetime(2025, 7, 3))
    
    # Token (not expired)
    token = PermissionToken(
        token="validtoken123",
        user_id=1,
        activity_id=1,
        expires_at=datetime.utcnow() + timedelta(days=1),
        used=False
    )

    db.add_all([user, activity, token])
    db.commit()


@patch("api.email.send_admin_confirmation")
@patch("api.pdf_func.generate_waiver_pdf")
def test_full_permission_flow(mock_pdf, mock_email):
    seed_test_data()

    # Step 1: Verify token
    res = client.get("/api/verify-token", params={"token": "validtoken123"})
    assert res.status_code == 200
    assert "activity_name" in res.json()

    # Step 2: Submit permission
    res = client.post("/api/submit-permission", json={"token": "validtoken123"}, headers={"user-agent": "TestAgent/1.0"})
    assert res.status_code == 200
    assert res.json()["status"] == "signed"

    # Step 3: Confirm PDF/email were called
    mock_pdf.assert_called_once()
    mock_email.assert_called_once()

    # Step 4: Check DB flags
    db = next(override_db())
    perm = db.query(ActivityPermission).filter_by(user_id=1, activity_id=1).first()
    assert perm is not None
    assert perm.signed
    assert perm.user_agent == "TestAgent/1.0"

    # Step 5: Token marked used
    token = db.query(PermissionToken).filter_by(token="validtoken123").first()
    assert token.used


def teardown_module(module):
    try:
        os.remove("test_flow.db")
    except FileNotFoundError:
        pass
    shutil.rmtree("./pdfs", ignore_errors=True)
