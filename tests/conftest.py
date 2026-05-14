from __future__ import annotations

import pytest

from src.db import SQLiteRepository
from src.init_db import create_database


@pytest.fixture()
def repository(tmp_path):
    db_path = create_database(tmp_path / "lab.sqlite3")
    return SQLiteRepository(db_path)
