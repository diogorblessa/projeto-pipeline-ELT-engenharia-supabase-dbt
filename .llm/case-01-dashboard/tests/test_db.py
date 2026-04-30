import pytest
import yaml
import pandas as pd
from unittest.mock import patch, mock_open
from sqlalchemy import create_engine, text


class TestGetEngine:
    def test_usa_postgres_url_quando_definida(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_URL", "postgresql://u:p@host:5432/db")
        import db
        import importlib
        importlib.reload(db)
        with patch("db.create_engine") as mock_engine:
            db.get_engine()
            mock_engine.assert_called_once_with("postgresql://u:p@host:5432/db")

    def test_fallback_para_profiles_yml(self, monkeypatch):
        monkeypatch.delenv("POSTGRES_URL", raising=False)
        profiles_yaml = yaml.dump({
            "ecommerce": {
                "outputs": {
                    "dev": {
                        "user": "myuser",
                        "password": "mypass",
                        "host": "myhost",
                        "port": 5432,
                        "dbname": "mydb",
                    }
                }
            }
        })
        import db
        import importlib
        importlib.reload(db)
        with patch("builtins.open", mock_open(read_data=profiles_yaml)), \
             patch("db.create_engine") as mock_engine:
            db.get_engine()
            mock_engine.assert_called_once_with(
                "postgresql://myuser:mypass@myhost:5432/mydb"
            )


class TestGetData:
    def test_retorna_dataframe(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE t (id INTEGER, val TEXT)"))
            conn.execute(text("INSERT INTO t VALUES (1, 'a')"))
            conn.execute(text("INSERT INTO t VALUES (2, 'b')"))
            conn.commit()

        import db
        with patch.object(db, "get_engine", return_value=engine):
            result = db.get_data("SELECT * FROM t")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["id", "val"]

    def test_resultado_vazio_e_dataframe(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE empty_t (id INTEGER)"))
            conn.commit()

        import db
        with patch.object(db, "get_engine", return_value=engine):
            result = db.get_data("SELECT * FROM empty_t")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
