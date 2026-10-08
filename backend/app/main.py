from fastapi import FastAPI

app = FastAPI(title="SecureBank AI", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "securebank-ai",
        "version": "0.1.0",
    }
