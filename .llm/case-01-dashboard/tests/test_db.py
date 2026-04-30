from unittest.mock import patch

import pandas as pd
import pytest
from sqlalchemy import create_engine, text


class TestGetEngine:
    def test_usa_postgres_url_quando_definida(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_URL", "postgresql://u:p@host:5432/db")
        import importlib

        import db
        importlib.reload(db)
        with patch("db.create_engine") as mock_engine:
            db.get_engine()
            mock_engine.assert_called_once_with("postgresql://u:p@host:5432/db")

    def test_levanta_erro_sem_postgres_url(self, monkeypatch):
        monkeypatch.delenv("POSTGRES_URL", raising=False)
        import importlib

        import db
        importlib.reload(db)
        with pytest.raises(RuntimeError, match="POSTGRES_URL"):
            db.get_engine()


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
