import pandas as pd
from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, text


def get_engine(postgres_url: SecretStr) -> Engine:
    return create_engine(postgres_url.get_secret_value())


def execute_query(sql: str, postgres_url: SecretStr) -> pd.DataFrame:
    sql_clean = sql.strip().upper()
    if not (sql_clean.startswith("SELECT") or sql_clean.startswith("WITH")):
        raise ValueError("Apenas SELECT/WITH são permitidos.")

    engine = get_engine(postgres_url)
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)
