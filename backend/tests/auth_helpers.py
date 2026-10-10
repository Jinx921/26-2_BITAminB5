from uuid import uuid4

from backend.app.auth import issue_token, password_hash


def authorization_headers(client, role: str = "citizen") -> dict[str, str]:
    email = f"{uuid4().hex}@example.com"
    user = client.app.state.database.create_user(
        email, "hash-unused-by-token-test", role=role
    )
    token = issue_token(user, client.app.state.jwt_secret)
    return {"Authorization": f"Bearer {token}"}


def login_as(client, role: str = "citizen") -> dict[str, str]:
    email = f"{uuid4().hex}@example.com"
    password = "test-password-for-ci"
    if role == "citizen":
        created = client.post(
            "/api/v1/auth/register", json={"email": email, "password": password}
        )
        assert created.status_code == 201, created.text
    else:
        client.app.state.database.create_user(
            email, password_hash.hash(password), role=role
        )
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
