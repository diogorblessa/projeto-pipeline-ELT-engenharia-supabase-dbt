import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


VALID_ENV_BASE = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_DB": "test",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pwd",
    "POSTGRES_SCHEMA": "main",  # SQLite usa "main" como schema padrao
    "S3_ENDPOINT_URL": "https://example.com",
    "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "key",
    "S3_SECRET_ACCESS_KEY": "secret",
    "S3_BUCKET": "test-bucket",
}


@pytest.fixture
def in_memory_engine_factory(monkeypatch):
    """SQLite :memory: que sobrevive a engine.dispose() chamado pelo load() em finally.

    StaticPool mantém uma única conexão (a tabela criada por to_sql sobrevive
    entre acessos). dispose() é neutralizado porque, em SQLite :memory:,
    descartar o pool destrói o database — em produção (Postgres) é o correto.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(engine, "dispose", lambda: None)

    def fake_create_engine(*args, **kwargs):
        return engine

    monkeypatch.setattr("extract_load.load.create_engine", fake_create_engine)
    return engine


def _make_settings(monkeypatch, **overrides):
    from extract_load.config import Settings

    env = {**VALID_ENV_BASE, **overrides}
    for k in list(VALID_ENV_BASE.keys()) + ["POSTGRES_PORT", "POSTGRES_SSLMODE", "LOG_LEVEL"]:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return Settings(_env_file=None)


def test_load_inserts_dataframes(in_memory_engine_factory, monkeypatch):
    from extract_load.load import load

    dfs = {
        "vendas": pd.DataFrame({"id_venda": [1, 2, 3], "valor": [10.0, 20.0, 30.0]}),
        "clientes": pd.DataFrame({"id_cliente": [1, 2], "nome": ["a", "b"]}),
    }
    settings = _make_settings(monkeypatch)
    load(dfs, settings)

    with in_memory_engine_factory.connect() as conn:
        n_vendas = conn.execute(text("SELECT COUNT(*) FROM main.vendas")).scalar()
        n_clientes = conn.execute(text("SELECT COUNT(*) FROM main.clientes")).scalar()
    assert n_vendas == 3
    assert n_clientes == 2


def test_load_replaces_existing_table(in_memory_engine_factory, monkeypatch):
    from extract_load.load import load

    settings = _make_settings(monkeypatch)
    load({"vendas": pd.DataFrame({"x": [1, 2, 3, 4, 5]})}, settings)
    load({"vendas": pd.DataFrame({"x": [1]})}, settings)

    with in_memory_engine_factory.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM main.vendas")).scalar()
    assert n == 1


def test_load_raises_load_error_on_failure(monkeypatch):
    from extract_load.load import LoadError, load

    # Engine que sempre falha
    bad_engine = create_engine("sqlite:///:memory:")
    bad_engine.dispose()  # forca conexoes a falharem

    def fake_create_engine(*args, **kwargs):
        return bad_engine

    monkeypatch.setattr("extract_load.load.create_engine", fake_create_engine)

    # DataFrame com tipos incompativeis com SQLite causa falha em to_sql
    # Caminho mais robusto: mockar to_sql diretamente via DataFrame
    dfs = {"vendas": pd.DataFrame({"x": [1]})}
    settings = _make_settings(monkeypatch)

    # Mock pd.DataFrame.to_sql para levantar
    from sqlalchemy.exc import SQLAlchemyError

    original_to_sql = pd.DataFrame.to_sql

    def fake_to_sql(self, *args, **kwargs):
        raise SQLAlchemyError("simulated failure")

    monkeypatch.setattr(pd.DataFrame, "to_sql", fake_to_sql)
    try:
        with pytest.raises(LoadError) as exc_info:
            load(dfs, settings)
        assert "vendas" in str(exc_info.value)
    finally:
        monkeypatch.setattr(pd.DataFrame, "to_sql", original_to_sql)
