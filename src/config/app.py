from pydantic import Field

from config.base import BaseAppSettings


class FastAPISettings(BaseAppSettings):
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    uc_log_level: str = Field(default="critical")
    api_key: str = Field(default="key")


class LoggerSettings(BaseAppSettings):
    log_level: str = Field(default="DEBUG")
    log_to_console: bool = Field(default=True)
    log_max_frames: int = Field(default=10)
