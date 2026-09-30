import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    main.ensure_database()
    target = tmp_path / "app.db"
    with sqlite3.connect(main.DB_PATH) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    monkeypatch.setattr(main, "DB_PATH", target)
    with TestClient(main.app, raise_server_exceptions=False) as test_client:
        yield test_client
