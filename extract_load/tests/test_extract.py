from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


VALID_ENV = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_DB": "test",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pwd",
    "S3_ENDPOINT_URL": "https://example.com",
    "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "key",
    "S3_SECRET_ACCESS_KEY": "secret",
    "S3_BUCKET": "test-bucket",
}


def _parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_parquet(buf, engine="pyarrow")
    return buf.getvalue()


def _make_settings(monkeypatch):
    from extract_load.config import Settings

    for k in list(VALID_ENV.keys()) + ["POSTGRES_PORT", "POSTGRES_SCHEMA",
                                        "POSTGRES_SSLMODE", "LOG_LEVEL"]:
        monkeypatch.delenv(k, raising=False)
    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    return Settings(_env_file=None)


@patch("extract_load.extract.boto3.client")
def test_extract_returns_four_dataframes(mock_boto, monkeypatch):
    from extract_load.extract import extract

    sample_df = pd.DataFrame({"id": [1, 2, 3]})
    payload = _parquet_bytes(sample_df)

    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: payload)}
    mock_boto.return_value = mock_s3

    settings = _make_settings(monkeypatch)
    result = extract(settings)

    assert set(result.keys()) == {"vendas", "clientes", "produtos", "preco_competidores"}
    for df in result.values():
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3


@patch("extract_load.extract.boto3.client")
def test_extract_passes_credentials_to_boto3(mock_boto, monkeypatch):
    from extract_load.extract import extract

    sample_df = pd.DataFrame({"id": [1]})
    payload = _parquet_bytes(sample_df)
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: payload)}
    mock_boto.return_value = mock_s3

    settings = _make_settings(monkeypatch)
    extract(settings)

    args, kwargs = mock_boto.call_args
    assert args == ("s3",)
    assert kwargs["region_name"] == "us-east-1"
    assert kwargs["endpoint_url"] == "https://example.com"
    assert kwargs["aws_access_key_id"] == "key"
    assert kwargs["aws_secret_access_key"] == "secret"


@patch("extract_load.extract.boto3.client")
def test_extract_raises_extract_error_on_s3_failure(mock_boto, monkeypatch):
    from botocore.exceptions import ClientError

    from extract_load.extract import ExtractError, extract

    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "not found"}}, "GetObject"
    )
    mock_boto.return_value = mock_s3

    settings = _make_settings(monkeypatch)
    with pytest.raises(ExtractError) as exc_info:
        extract(settings)
    assert "vendas" in str(exc_info.value)  # contexto: qual tabela falhou
