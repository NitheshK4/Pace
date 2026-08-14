import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status
from app.main import app

@pytest.mark.asyncio
async def test_auth_me_authenticated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        reg_resp = await ac.post("/v1/auth/register", json={
            "email": "me_user@example.com",
            "password": "Password123!",
            "full_name": "Session User"
        })
        assert reg_resp.status_code == status.HTTP_201_CREATED

        login_resp = await ac.post("/v1/auth/login", json={
            "email": "me_user@example.com",
            "password": "Password123!"
        })
        assert login_resp.status_code == status.HTTP_200_OK
        token = login_resp.json()["access_token"]

        me_resp = await ac.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.status_code == status.HTTP_200_OK
        data = me_resp.json()
        assert data["email"] == "me_user@example.com"
        assert "id" in data

@pytest.mark.asyncio
async def test_auth_me_unauthenticated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v1/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
