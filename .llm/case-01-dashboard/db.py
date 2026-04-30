import os

import pandas as pd
from sqlalchemy import create_engine, text


def get_engine():
    url = os.getenv("POSTGRES_URL")
    if not url:
        raise RuntimeError(
            "POSTGRES_URL nao configurada. Defina no .env da raiz do projeto."
        )
    return create_engine(url)


def get_data(query: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)
