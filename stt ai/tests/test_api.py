"""
End-to-end API tests for VaultAI.
Run with: python -m pytest tests/test_api.py -v
"""
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["OPENAI_API_KEY"] = "sk-test-dummy"
os.environ["VAULTAI_SKIP_WARMUP"] = "1"

from fastapi.testclient import TestClient
import pytest

from backend.database import Base, engine, SessionLocal
from backend.main import app


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    test_db = Path("test.db")
    for _ in range(5):
        try:
            if test_db.exists():
                test_db.unlink()
            break
        except PermissionError:
            import time
            time.sleep(0.5)


client = TestClient(app, raise_server_exceptions=False)


class TestHealth:
    def test_health_check(self):
        response = client.get("/admin/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuth:
    def test_register(self):
        response = client.post("/auth/register", json={"email": "test@example.com", "password": "testpass123"})
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["plan"] == "free"
        assert "id" in data

    def test_register_duplicate(self):
        client.post("/auth/register", json={"email": "dup@example.com", "password": "testpass123"})
        response = client.post("/auth/register", json={"email": "dup@example.com", "password": "testpass123"})
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_login(self):
        client.post("/auth/register", json={"email": "login@example.com", "password": "testpass123"})
        response = client.post("/auth/login", json={"email": "login@example.com", "password": "testpass123"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid(self):
        response = client.post("/auth/login", json={"email": "noone@example.com", "password": "wrong"})
        assert response.status_code == 401


class TestUpload:
    def _auth_token(self):
        client.post("/auth/register", json={"email": "upload@example.com", "password": "testpass123"})
        resp = client.post("/auth/login", json={"email": "upload@example.com", "password": "testpass123"})
        return resp.json()["access_token"]

    def test_upload_no_auth(self):
        response = client.post("/upload/audio", files={"file": ("test.mp3", b"fakeaudiodata", "audio/mpeg")})
        assert response.status_code in (401, 403)

    def test_upload_invalid_format(self):
        token = self._auth_token()
        response = client.post(
            "/upload/audio",
            files={"file": ("test.txt", b"not an audio file", "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=True,
        )
        assert response.status_code == 400

    def test_jobs_empty(self):
        token = self._auth_token()
        response = client.get(
            "/ingest/jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestVaults:
    def _auth_token(self):
        client.post("/auth/register", json={"email": "vault@example.com", "password": "testpass123"})
        resp = client.post("/auth/login", json={"email": "vault@example.com", "password": "testpass123"})
        return resp.json()["access_token"]

    def test_vaults_empty(self):
        token = self._auth_token()
        response = client.get("/vaults", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_vault_not_found(self):
        token = self._auth_token()
        response = client.get("/vaults/nonexistent", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 404


class TestQuery:
    def _auth_token(self):
        client.post("/auth/register", json={"email": "query@example.com", "password": "testpass123"})
        resp = client.post("/auth/login", json={"email": "query@example.com", "password": "testpass123"})
        return resp.json()["access_token"]

    def test_query_no_auth(self):
        response = client.post("/query/ask", json={"podcast_id": "test123", "question": "What is this about?"})
        assert response.status_code in (401, 403)

    def test_query_nonexistent_vault(self):
        token = self._auth_token()
        response = client.post(
            "/query/ask",
            json={"podcast_id": "nonexistent", "question": "What is this about?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
