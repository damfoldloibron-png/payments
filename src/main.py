import uvicorn

from config import settings
from config.log_conf import setup_logging

setup_logging()

if __name__ == "__main__":
    uvicorn.run(
        "app:create_app",
        factory=True,
        host=settings.api.host,
        port=settings.api.port,
        log_level=settings.api.uc_log_level,
    )
