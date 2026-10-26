from urllib.parse import quote

from pydantic import Field, SecretStr

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


class DatabaseSettings(BaseAppSettings):
    db_dialect: str = Field("postgresql")
    db_driver: str = Field("asyncpg")
    db_user: str | None = Field(default=None)
    db_password: SecretStr | None = Field(default=None)
    db_host: str = Field("localhost")
    db_port: int = Field(5432)
    db_name: str | None = Field(default=None)

    db_echo: bool = Field(False)
    db_pool_size: int = Field(5)
    db_max_overflow: int = Field(10)
    db_connect_timeout: int = Field(30)

    @property
    def sqlalchemy_url(self) -> str:
        password = self.db_password.get_secret_value() if self.db_password else ""
        user = self.db_user or ""
        name = self.db_name or ""
        return (
            f"{self.db_dialect}+{self.db_driver}://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{name}"
        )


class RabbitSettings(BaseAppSettings):
    rabbit_host: str = Field("localhost")
    rabbit_port: int = Field(5672)
    rabbit_user: str = Field("guest")
    rabbit_password: SecretStr = Field(SecretStr("guest"))
    rabbit_vhost: str = Field("/")
    rabbit_prefetch_count: int = Field(10)

    @property
    def rabbit_url(self) -> str:
        password = self.rabbit_password.get_secret_value()
        vhost = quote(self.rabbit_vhost, safe="")
        return (
            f"amqp://{self.rabbit_user}:{password}"
            f"@{self.rabbit_host}:{self.rabbit_port}/{vhost}"
        )


class RelaySettings(BaseAppSettings):
    relay_batch_size: int = Field(100)
    relay_poll_interval: float = Field(1.0)
    relay_publish_timeout: float = Field(5.0)
    outbox_retention_hours: float = Field(24.0)
    outbox_cleanup_interval: float = Field(3600.0)
    outbox_cleanup_batch: int = Field(1000)


class WebhookSettings(BaseAppSettings):
    webhook_timeout: float = Field(5.0)


class RetrySettings(BaseAppSettings):
    retry_max_attempts: int = Field(3)
    retry_base_delay: float = Field(5.0)
    retry_factor: float = Field(2.0)

    @property
    def retry_delays(self) -> tuple[float, ...]:
        """Задержки между попытками: base * factor**i, всего попыток минус одна"""
        return tuple(
            self.retry_base_delay * self.retry_factor**i
            for i in range(self.retry_max_attempts - 1)
        )
