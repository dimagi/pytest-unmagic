# examples/basic/test_scope.py
"""Fixture scope examples.

Run: pytest examples/basic/test_scope.py -v -s
"""
from unmagic import fixture

setup_count = 0


@fixture(scope="module")
def shared_resource():
    """Set up once for the entire module."""
    global setup_count
    setup_count += 1
    yield {"id": setup_count}


def test_first():
    resource = shared_resource()
    assert resource["id"] == 1


def test_second():
    resource = shared_resource()
    # Same instance -- module scope means one setup per module
    assert resource["id"] == 1


def test_setup_only_once():
    assert setup_count == 1
