from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DeepBSV central configuration loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    env: str = Field(default="development", alias="DEEPBSV_ENV")
    log_level: str = Field(default="INFO", alias="DEEPBSV_LOG_LEVEL")

    # BSV Node RPC
    rpc_host: str = Field(default="127.0.0.1", alias="BSV_RPC_HOST")
    rpc_port: int = Field(default=8332, alias="BSV_RPC_PORT")
    rpc_user: str = Field(default="deepbsv_user", alias="BSV_RPC_USER")
    rpc_password: str = Field(default="", alias="BSV_RPC_PASSWORD")
    rpc_timeout: float = Field(default=10.0, alias="BSV_RPC_TIMEOUT")

    @property
    def rpc_url(self) -> str:
        return f"http://{self.rpc_host}:{self.rpc_port}"


settings = Settings()
