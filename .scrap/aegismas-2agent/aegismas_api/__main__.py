"""Entry point for running as module"""
from .main import app
import uvicorn
from .config import config

if __name__ == "__main__":
    uvicorn.run(
        "aegismas_api.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
    )

