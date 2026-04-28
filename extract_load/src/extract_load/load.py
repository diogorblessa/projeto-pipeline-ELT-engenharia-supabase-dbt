import logging

import pandas as pd
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from extract_load.config import Settings

log = logging.getLogger(__name__)


class LoadError(Exception):
    """Raised when loading to PostgreSQL fails."""


def _build_url(settings: Settings) -> URL:
    return URL.create(
        drivername="postgresql+psycopg2",
        username=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )


def load(dfs: dict[str, pd.DataFrame], settings: Settings) -> None:
    """Replace tables in `settings.postgres_schema` with the given DataFrames."""
    url = _build_url(settings)
    connect_args = {"sslmode": settings.postgres_sslmode}
    engine = create_engine(url, connect_args=connect_args)
    try:
        for tabela, df in dfs.items():
            try:
                df.to_sql(
                    tabela,
                    engine,
                    schema=settings.postgres_schema,
                    if_exists="replace",
                    index=False,
                )
            except SQLAlchemyError as e:
                raise LoadError(f"failed to load {tabela}: {e}") from e
            log.info(
                "loaded: %s (%d rows -> %s.%s)",
                tabela,
                len(df),
                settings.postgres_schema,
                tabela,
            )

        # Verificacao final
        with engine.connect() as conn:
            for tabela in dfs:
                qualified = f"{settings.postgres_schema}.{tabela}"
                count = conn.execute(text(f"SELECT COUNT(*) FROM {qualified}")).scalar()  # noqa: S608
                log.info("verified: %s = %s rows", qualified, count)
    finally:
        engine.dispose()
