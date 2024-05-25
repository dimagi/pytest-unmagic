from contextlib import contextmanager

import pytest
from _pytest.capture import capsys
from _pytest.outcomes import Failed

from unmagic import fence, fixture, get_fixture_value, use

from .util import get_source


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


@use(tracer, check_done)
def test_unmagic_fixture_with_more_fixtures_than_args(traces):
    traces.append("done")


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

    with pytest.raises(Failed, match="fixture 'broken_fix' does not yield"):
        test(request=request)


def test_malformed_unmagic_fixture_as_context_manager():
    with pytest.raises(TypeError, match="fixture 'broken_fix' does not yield"):
        with broken_fix():
            assert 0, "should not get here"


def test_get_fixture_value_with_unmagic_fixture():
    with pytest.raises(ValueError, match="name must be a string"):
        get_fixture_value(tracer)


class TestMethodUse:

    @use(tracer, check_done)
    def test_use(self, traces):
        traces.append("done")


def test_class_and_session_scope():
    @get_source
    def test_py():
        from unmagic import fixture, get_fixture_value, use

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture(scope="class")
        @use(ss_tracer)
        def cls_fix(traces):
            name = get_fixture_value("request").cls.__name__[-1]
            traces.append(f"{name}-a")
            yield name
            traces.append(f"{name}-z")

        class TestX:
            @use(ss_tracer)
            def test_one(self, tr):
                tr.append("x1")

            @use(ss_tracer, cls_fix)
            def test_two(self, tr, fix):
                tr.append(f"{fix}-x2")

            @use(ss_tracer)
            def test_three(self, tr):
                tr.append("x3")

        class TestY:
            @use(ss_tracer)
            def test_one(self, tr):
                tr.append("y1")

            @use(ss_tracer, cls_fix)
            def test_two(self, tr, fix):
                tr.append(f"{fix}-y2")

            @use(ss_tracer)
            def test_three(self, tr):
                tr.append("y3")

    pytester = get_fixture_value("pytester")
    pytester.makepyfile(test_py)
    result = pytester.runpytest("-s", "-punmagic.scope")
    result.stdout.fnmatch_lines([
        "* x1 X-a X-x2 x3 X-z y1 Y-a Y-y2 y3 Y-z",
    ])
    result.assert_outcomes(passed=6)


def test_module_scope():
    @get_source
    def fix_py():
        from unmagic import fixture, get_fixture_value, use

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture(scope="module")
        @use(ss_tracer)
        def mod_fix(traces):
            name = get_fixture_value("request").module.__name__[-4:]
            traces.append(f"{name}-a")
            yield name
            traces.append(f"{name}-z")

    @get_source
    def mod1_py():
        from unmagic import use
        from fix import ss_tracer, mod_fix

        @use(ss_tracer)
        def test_one(tr):
            tr.append("x1")

        @use(ss_tracer, mod_fix)
        def test_two(tr, fix):
            tr.append(f"{fix}-x2")

        @use(ss_tracer)
        def test_three(tr):
            tr.append("x3")

    @get_source
    def mod2_py():
        from unmagic import use
        from fix import ss_tracer, mod_fix

        @use(ss_tracer)
        def test_one(tr):
            tr.append("y1")

        @use(ss_tracer, mod_fix)
        def test_two(tr, fix):
            tr.append(f"{fix}-y2")

        @use(ss_tracer)
        def test_three(tr):
            tr.append("y3")

    pytester = get_fixture_value("pytester")
    pytester.makepyfile(fix=fix_py, test_mod1=mod1_py, test_mod2=mod2_py)

    result = pytester.runpytest("-s", "-punmagic.scope")
    result.stdout.fnmatch_lines([
        "* x1 mod1-a mod1-x2 x3 mod1-z y1 mod2-a mod2-y2 y3 mod2-z",
    ])
    result.assert_outcomes(passed=6)


def test_setup_function(request):
    @get_source
    def test_py():
        from unmagic import fixture, get_fixture_value, use

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture
        @use(ss_tracer)
        def fun_fix(traces):
            name = f"t{get_fixture_value('request').function.__name__[-1]}"
            traces.append(f"{name}-a")
            yield name
            traces.append(f"{name}-z")

        @use(ss_tracer, fun_fix)
        def setup_function(tr, ff):
            tr.append("sf")

        @use(ss_tracer)
        def test_x0(tr):
            tr.append("x0")

        @use(ss_tracer)
        def test_x1(tr):
            tr.append("x1")

        @use(ss_tracer, fun_fix)
        def test_x2(tr, ff):
            tr.append(f"x2-{ff}")

    pytester = request.getfixturevalue("pytester")
    pytester.makepyfile(test_py)
    result = pytester.runpytest("-sl", "--tb=long", "-punmagic.scope")
    result.stdout.fnmatch_lines([
        "* t0-a sf x0 t0-z t1-a sf x1 t1-z t2-a sf x2-t2 t2-z",
    ])
    result.assert_outcomes(passed=3)
