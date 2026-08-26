"""End-to-end test of the login + protected-access flow, against a real
FastAPI app instance and a real (isolated) Postgres database — no mocks.

Backend counterpart to frontend/e2e/auth.spec.ts, which drives the same
flow through the browser; this exercises the HTTP contract directly.
"""

from httpx import AsyncClient


async def test_register_login_access_refresh_logout_round_trip(
    client: AsyncClient, test_user_credentials: dict
) -> None:
    """The full happy path a real client goes through, in order."""
    register_response = await client.post("/auth/register", json=test_user_credentials)
    assert register_response.status_code == 201
    registered_user = register_response.json()
    assert registered_user["username"] == test_user_credentials["username"]
    assert registered_user["status"] == "active"

    login_response = await client.post(
        "/auth/login",
        json={
            "identifier": test_user_credentials["username"],
            "password": test_user_credentials["password"],
        },
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["user"]["id"] == registered_user["id"]
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    me_response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["user"]["id"] == registered_user["id"]
    assert me_body["roles"] == []
    assert me_body["permissions"] == []

    refresh_response = await client.post(
        "/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    rotated = refresh_response.json()
    new_access_token = rotated["access_token"]
    new_refresh_token = rotated["refresh_token"]
    assert new_access_token != access_token
    assert new_refresh_token != refresh_token

    # The new access token must actually work.
    me_after_refresh = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert me_after_refresh.status_code == 200

    # The rotated-away refresh token must be dead, not just superseded.
    reuse_old_refresh = await client.post(
        "/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert reuse_old_refresh.status_code == 401

    logout_response = await client.post(
        "/auth/logout", json={"refresh_token": new_refresh_token}
    )
    assert logout_response.status_code == 204

    # Logout must actually revoke the session: the current refresh token no
    # longer works either.
    refresh_after_logout = await client.post(
        "/auth/refresh", json={"refresh_token": new_refresh_token}
    )
    assert refresh_after_logout.status_code == 401


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_rejects_garbage_token(client: AsyncClient) -> None:
    response = await client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


async def test_login_rejects_wrong_password(
    client: AsyncClient, test_user_credentials: dict
) -> None:
    register_response = await client.post("/auth/register", json=test_user_credentials)
    assert register_response.status_code == 201

    login_response = await client.post(
        "/auth/login",
        json={
            "identifier": test_user_credentials["username"],
            "password": "definitely-the-wrong-password",
        },
    )
    assert login_response.status_code == 401


async def test_login_rejects_unknown_user(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login",
        json={"identifier": "no-such-user", "password": "whatever-password"},
    )
    assert response.status_code == 401


async def test_duplicate_registration_conflicts(
    client: AsyncClient, test_user_credentials: dict
) -> None:
    first = await client.post("/auth/register", json=test_user_credentials)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=test_user_credentials)
    assert second.status_code == 409


async def test_auth_headers_fixture_reaches_the_protected_route(
    client: AsyncClient, auth_headers: dict, test_user_credentials: dict
) -> None:
    """Sanity check on the shared fixture itself, not just ad hoc calls above."""
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["user"]["username"] == test_user_credentials["username"]
