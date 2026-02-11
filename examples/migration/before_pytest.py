# examples/migration/before_pytest.py
"""
Before Migration: Standard pytest fixture patterns

This file shows common pytest patterns. Compare with after_unmagic.py
to see the equivalent pytest-unmagic code.

.. note::

   This file is for illustration. It references fixtures that would
   normally be in conftest.py.

"""
import pytest


# 1. Basic fixture
@pytest.fixture
def db():
    connection = {"connected": True, "data": {}}
    yield connection
    connection["connected"] = False


# 2. Fixture with scope
@pytest.fixture(scope="module")
def app():
    application = {"started": True}
    yield application
    application["started"] = False


# 3. Autouse fixture
@pytest.fixture(autouse=True)
def clean_state():
    yield
    # cleanup after each test


# 4. Fixture using another fixture
@pytest.fixture
def admin_user(db):
    user = {"name": "admin"}
    db["data"]["admin"] = user
    yield user


# 5. Test using fixtures via argument injection
def test_query(db):
    db["data"]["key"] = "value"
    assert db["data"]["key"] == "value"


def test_admin(admin_user, db):
    assert db["data"]["admin"] == admin_user


# 6. Class-based test
class TestApp:
    def test_started(self, app):
        assert app["started"] is True
