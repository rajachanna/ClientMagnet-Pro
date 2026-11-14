from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from clientmagnet.api import create_app
from clientmagnet.config import Settings

KEY = "clientmagnet-testing-operator-key-abcdefghijk"
AUTH = {"X-Operator-Key": KEY}

@pytest.fixture
def settings(tmp_path):
    return Settings(db_path=tmp_path / "test.sqlite", operator_key=KEY)

@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as value:
        yield value
