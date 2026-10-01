from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvTypes(StrEnum):
    prod = "prod"
    dev = "dev"
    test = "test"


class BaseAppSettings(BaseSettings):
    app_env: AppEnvTypes = AppEnvTypes.prod

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
