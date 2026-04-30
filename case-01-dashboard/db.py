import os
import yaml
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text


def get_engine():
    url = os.getenv("POSTGRES_URL")
    if url:
        return create_engine(url)
    profiles_path = Path.home() / ".dbt" / "profiles.yml"
    with open(profiles_path) as f:
        profiles = yaml.safe_load(f)
    dev = profiles["ecommerce"]["outputs"]["dev"]
    url = (
        f"postgresql://{dev['user']}:{dev['password']}"
        f"@{dev['host']}:{dev['port']}/{dev['dbname']}"
    )
    return create_engine(url)


def get_data(query: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)
