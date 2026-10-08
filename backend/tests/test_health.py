import asyncio

from httpx import ASGITransport, AsyncClient, Response

from app.main import app


def test_health_contract() -> None:
    async def request_health() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "securebank-ai",
        "version": "0.1.0",
    }
