# examples/migration/after_unmagic.py
"""
After Migration: pytest-unmagic equivalents

Compare with before_pytest.py. Run this file:

    pytest examples/migration/after_unmagic.py -v

"""
from unmagic import fixture, use


# 1. Basic fixture -- @pytest.fixture -> @fixture, return -> yield
@fixture
def db():
    connection = {"connected": True, "data": {}}
    yield connection
    connection["connected"] = False


# 2. Fixture with scope -- same scope parameter
@fixture(scope="module")
def app():
    application = {"started": True}
    yield application
    application["started"] = False


# 3. Autouse fixture -- autouse=__file__ limits to this module
@fixture(autouse=__file__)
def clean_state():
    yield
    # cleanup after each test


# 4. Fixture using another fixture -- @use chains dependencies
@use(db)
@fixture
def admin_user():
    database = db()  # call to get value (not argument injection)
    user = {"name": "admin"}
    database["data"]["admin"] = user
    yield user


# 5. Tests -- no arguments, fixtures called explicitly
def test_query():
    database = db()
    database["data"]["key"] = "value"
    assert database["data"]["key"] == "value"


@use(admin_user)
def test_admin():
    user = admin_user()
    database = db()
    assert database["data"]["admin"] == user


# 6. Class-based test -- @use on class applies to all methods
@use(app)
class TestApp:
    def test_started(self):
        application = app()
        assert application["started"] is True
