from contextlib import contextmanager

import pytest
from _pytest.capture import capsys

from unmagic import fence, fixture, use


@fixture
def tracer():
    yield []


@fixture
@use(tracer)
def fix(traces):
    traces.append("fixing...")
    yield "fixed value"
    traces.append("fix done")


@use(tracer)
@fixture
def check_done(traces):
    yield
    assert traces[-1].endswith("done")


@use(check_done, fix, tracer)
def test_unmagic_fixture(_, fixed, traces):
    assert fixed == "fixed value"
    assert traces == ["fixing..."]


def test_unmagic_fixture_as_context_manager():
    with tracer() as traces:
        assert traces == []


@pytest.mark.parametrize("p1, p2", [(1, 2), (2, 3)])
@use(tracer, check_done)
def test_params(traces, _, p1, p2):
    assert p1 + 1 == p2
    traces.append("done")


@contextmanager
def plain_context():
    yield "other"


@contextmanager
@use(tracer)
def plain_context_using_fixture(traces):
    yield traces


@use(plain_context_using_fixture, tracer, plain_context)
def test_plain_contextmanager_fixture(context_traces, traces, other):
    assert context_traces is traces
    assert other == "other"


def test_module_is_fenced():
    assert fence.is_fenced(test_module_is_fenced)


@use(capsys)
def test_use_magic_fixture(cap):
    print("hello")
    captured = cap.readouterr()
    assert captured.out == "hello\n"


@fixture
def broken_fix():
    return "nope"


def test_malformed_unmagic_fixture(request):
    @use(broken_fix)
    def test(value):
        assert 0, "should not get here"

    with pytest.raises(TypeError, match="fixture 'broken_fix' does not yield"):
        test(request=request)


def test_malformed_unmagic_fixture_as_context_manager():
    with pytest.raises(TypeError, match="fixture 'broken_fix' does not yield"):
        with broken_fix():
            assert 0, "should not get here"
