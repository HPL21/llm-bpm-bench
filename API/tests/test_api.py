import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test endpointu systemowego /health."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_test_suite(client: AsyncClient):
    """Test tworzenia nowego zbioru testowego (CRUD)."""
    payload = {
        "name": "Testowy Zbiór Unit Tests",
        "description": "Opis testowy",
        "system_prompt": "Jesteś pomocnym asystentem.",
    }

    response = await client.post("/api/v1/suites/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert "id" in data


@pytest.mark.asyncio
async def test_read_test_suites(client: AsyncClient):
    """Test pobierania listy zbiorów."""
    payload = {"name": "Zbiór do odczytu", "system_prompt": "X"}
    await client.post("/api/v1/suites/", json=payload)

    response = await client.get("/api/v1/suites/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
