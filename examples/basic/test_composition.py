# examples/basic/test_composition.py
"""Fixture composition examples.

Run: pytest examples/basic/test_composition.py -v
"""
from unmagic import fixture, use


@fixture
def database():
    db = {"users": []}
    yield db
    db["users"].clear()


@use(database)
@fixture
def admin_user():
    db = database()
    user = {"name": "admin", "role": "admin"}
    db["users"].append(user)
    yield user


def test_admin_exists():
    user = admin_user()
    assert user["name"] == "admin"
    assert user["role"] == "admin"


def test_database_has_admin():
    admin = admin_user()
    db = database()
    assert admin in db["users"]
