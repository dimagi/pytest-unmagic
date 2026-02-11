# examples/basic/test_simple.py
"""Basic fixture usage examples.

Run: pytest examples/basic/test_simple.py -v
"""
from unmagic import fixture, use


@fixture
def greeting():
    yield "hello"


# Call a fixture to retrieve its value
def test_greeting_value():
    value = greeting()
    assert value == "hello"


# Apply a fixture with @use for side effects
traces = []


@fixture
def tracer():
    traces.clear()
    yield
    # teardown: traces are available here


@use(tracer)
def test_tracing():
    traces.append("one")
    assert traces == ["one"]


# Shorthand: use fixture directly as decorator
@tracer
def test_shorthand():
    traces.append("two")
    assert traces == ["two"]
