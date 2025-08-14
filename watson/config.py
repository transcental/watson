from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class SlackConfig(BaseSettings):
    bot_token: str
    channel_id: str


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="allow")
    slack: SlackConfig
    environment: str = "development"
    port: int = 3000
    secret_key: str


config = Config()  # type: ignore
