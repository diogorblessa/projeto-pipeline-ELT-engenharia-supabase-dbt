import io
import logging

import boto3
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError

from extract_load.config import TABELAS, Settings

log = logging.getLogger(__name__)


class ExtractError(Exception):
    """Raised when extraction from S3 fails."""


def _build_s3_client(settings: Settings):
    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
    )


def extract(settings: Settings) -> dict[str, pd.DataFrame]:
    """Download 4 Parquet files from S3 and return as DataFrames keyed by table name."""
    s3 = _build_s3_client(settings)
    dfs: dict[str, pd.DataFrame] = {}

    for tabela in TABELAS:
        key = f"{tabela}.parquet"
        try:
            response = s3.get_object(Bucket=settings.s3_bucket, Key=key)
            payload = response["Body"].read()
            df = pd.read_parquet(io.BytesIO(payload))
        except (BotoCoreError, ClientError) as e:
            raise ExtractError(f"failed to extract {tabela}: {e}") from e

        dfs[tabela] = df
        log.info("extracted: %s (%d rows)", tabela, len(df))

    return dfs
