import pytest
from pydantic import ValidationError


VALID_ENV = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_DB": "test",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pwd_secret_value",
    "S3_ENDPOINT_URL": "https://example.com",
    "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "key_secret_value",
    "S3_SECRET_ACCESS_KEY": "ssk_secret_value",
    "S3_BUCKET": "bucket",
}


@pytest.fixture
def clean_env(monkeypatch):
    """Garante env limpo, sem ler .env do projeto."""
    for k in list(VALID_ENV.keys()) + ["POSTGRES_PORT", "POSTGRES_SCHEMA",
                                        "POSTGRES_SSLMODE", "LOG_LEVEL"]:
        monkeypatch.delenv(k, raising=False)


def test_settings_loads_from_env(monkeypatch, clean_env):
    from extract_load.config import Settings

    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    settings = Settings(_env_file=None)

    assert settings.postgres_host == "localhost"
    assert settings.postgres_db == "test"
    assert settings.postgres_user == "user"
    assert settings.postgres_password.get_secret_value() == "pwd_secret_value"
    assert settings.postgres_port == 5432  # default
    assert settings.postgres_schema == "public"  # default
    assert settings.postgres_sslmode == "require"  # default
    assert settings.s3_bucket == "bucket"
    assert settings.log_level == "INFO"  # default


def test_settings_missing_required_var_raises(monkeypatch, clean_env):
    from extract_load.config import Settings

    minimal = {k: v for k, v in VALID_ENV.items() if k != "POSTGRES_PASSWORD"}
    for k, v in minimal.items():
        monkeypatch.setenv(k, v)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_secrets_not_in_repr(monkeypatch, clean_env):
    from extract_load.config import Settings

    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    settings = Settings(_env_file=None)
    rendered = repr(settings)

    assert "pwd_secret_value" not in rendered
    assert "key_secret_value" not in rendered
    assert "ssk_secret_value" not in rendered


def test_tabelas_constant_is_correct():
    from extract_load.config import TABELAS

    assert TABELAS == ("vendas", "clientes", "produtos", "preco_competidores")
