from contextlib import contextmanager

import pytest

from unmagic import fixture, use


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


@pytest.mark.parametrize("p1, p2", [(1, 2), (2, 3)])
@use(tracer, check_done)
def test_params(traces, _, p1, p2):
    assert p1 + 1 == p2
    traces.append("done")


@contextmanager
@use(tracer)
def plain_context(traces):
    yield traces


@use(plain_context, tracer)
def test_plain_contextmanager_fixture(context_traces, traces):
    # NOTE fixture values of plain context managers are not cached and
    # shared with tests and their fixtures.
    assert context_traces is not traces
