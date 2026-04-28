from typing import Final

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

TABELAS: Final[tuple[str, ...]] = ("vendas", "clientes", "produtos", "preco_competidores")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # PostgreSQL
    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr
    postgres_schema: str = "public"
    postgres_sslmode: str = "require"

    # S3 / Supabase Storage
    s3_endpoint_url: str
    s3_region: str
    s3_access_key_id: SecretStr
    s3_secret_access_key: SecretStr
    s3_bucket: str

    # Logging
    log_level: str = "INFO"
