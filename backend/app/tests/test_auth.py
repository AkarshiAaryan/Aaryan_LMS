import pytest
from fastapi import status


DEMO_ACCOUNTS = [
    ("admin01", "admin", "Alex Admin"),
    ("prof01", "professor", "Dr Mira Shah"),
    ("prof02", "professor", "Dr Kabir Rao"),
    ("ta01", "ta", "Sam Lee"),
    ("ta02", "ta", "Noor Khan"),
    ("ta03", "ta", "Dev Patel"),
    ("ta04", "ta", "Elena Rostova"),
    ("student01", "student", "Asha Mehta"),
    ("student02", "student", "Rohan Das"),
    ("student03", "student", "Isha Roy"),
    ("student04", "student", "Vikram Sen"),
    ("student05", "student", "Tara Bose"),
    ("student06", "student", "Arjun Nair"),
    ("student07", "student", "Priya Sharma"),
    ("student08", "student", "Marcus Chen"),
    ("student09", "student", "Fatima Zahra"),
    ("student10", "student", "Lucas Silva"),
    ("student11", "student", "Chloe Bennett"),
    ("student12", "student", "David Kim"),
    ("student13", "student", "Ananya Iyer"),
    ("student14", "student", "Omar Farooq"),
    ("student15", "student", "Sofia Morales"),
    ("student16", "student", "Kevin Zhao"),
]


@pytest.mark.parametrize("username,expected_role,expected_name", DEMO_ACCOUNTS)
def test_login_all_demo_accounts(client, username, expected_role, expected_name):
    """Verify that all 23 synthetic demo accounts authenticate successfully."""
    response = client.post(
        "/auth/login",
        json={"username": username, "password": "GuardSLM2026!"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == username
    assert data["user"]["role"] == expected_role
    assert data["user"]["full_name"] == expected_name


def test_login_invalid_password(client):
    """Verify that invalid password returns 401 Unauthorized."""
    response = client.post(
        "/auth/login",
        json={"username": "student01", "password": "WrongPassword123!"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Verify that non-existent username returns 401."""
    response = client.post(
        "/auth/login",
        json={"username": "ghost_user", "password": "GuardSLM2026!"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_auth_me_authenticated(client, auth_headers):
    """Verify /auth/me returns current user identity."""
    headers = auth_headers("student01", "student", 7)
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "student01"
    assert data["role"] == "student"


def test_auth_me_unauthenticated(client):
    """Verify /auth/me without token returns 401."""
    response = client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_auth_me_tampered_token(client):
    """Verify that forged/tampered token is rejected."""
    headers = {"Authorization": "Bearer fake.tampered.token"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout(client, auth_headers):
    """Verify logout records session termination."""
    headers = auth_headers("admin01", "admin", 1)
    response = client.post("/auth/logout", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Logged out successfully."
