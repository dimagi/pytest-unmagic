from contextlib import contextmanager
from unittest.mock import patch

import pytest
from _pytest.capture import capsys
from _pytest.outcomes import Failed

from unmagic import fence, fixture, pytest_request, use

from .util import get_source, unmagic_tester


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
    assert test_unmagic_fixture.unmagic_fixtures == [check_done, fix, tracer]


@use(tracer, check_done)
def test_unmagic_fixture_with_more_fixtures_than_args(traces):
    traces.append("done")


@pytest.mark.parametrize("p1, p2", [(1, 2), (2, 3)])
@use(tracer, check_done)
def test_params(traces, _, p1, p2):
    assert p1 + 1 == p2
    traces.append("done")


@check_done
@fix
@tracer
def test_unmagic_fixture_as_decorator(traces, fixed):
    assert traces == ["fixing..."]
    assert fixed == "fixed value"
    assert test_unmagic_fixture_as_decorator.unmagic_fixtures \
        == [tracer, check_done]


class Thing:
    x = 0
    y = 4000
    z = -1


@fixture
def get_things():
    yield (Thing.x, Thing.y, Thing.z)


@fixture
@use(
    patch.object(Thing, "x", 2),
    get_things,
    patch.object(Thing, "z"),
)
def patch_things(xmock, things, zmock):
    assert Thing.x == 2
    yield things
    assert Thing.z is zmock


@patch_things
@patch.object(Thing, "y")
def test_patch_with_unmagic_fixture(things, mock):
    # applying fixtures and patches as decorators can have surprising outcomes
    # note: 'mock' argument is second because of the way patch applies args
    # note: patch_things is setup before Thing.y patch is applied
    assert things == (2, 4000, -1)
    assert Thing.y is mock


@contextmanager
def plain_context():
    yield "other"


@use(plain_context)
def test_plain_contextmanager_fixture(other):
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


@use(pytest_request)
def test_malformed_unmagic_fixture(request):
    @use(broken_fix)
    def test(value):
        assert 0, "should not get here"

    with pytest.raises(Failed, match="fixture 'broken_fix' does not yield"):
        test(request=request)


def test_malformed_unmagic_fixture_get_value():
    with pytest.raises(TypeError, match="fixture 'broken_fix' does not yield"):
        broken_fix()


@unmagic_tester
def test_fixture_get_value(pytester):
    @get_source
    def test_py():
        from unmagic import fixture, use

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture(scope="module")
        @use(ss_tracer)
        def mod_fix(traces):
            name = "mod"
            traces.append(f"{name}-a")
            yield name
            traces.append(f"{name}-z")

        @use(ss_tracer)
        def test_x0(tr):
            val = mod_fix()
            assert val == "mod"
            tr.append("x0")

        @use(ss_tracer)
        def test_x1(tr):
            tr.append("x1")
            val = mod_fix()
            assert val == "mod"

    pytester.makepyfile(test_py)
    result = pytester.runpytest("-sl", "--tb=long", "--setup-show")
    result.stdout.fnmatch_lines([
        "* mod-a x0 x1 mod-z",
    ])
    result.assert_outcomes(passed=2)


class TestMethodUse:

    @use(tracer, check_done)
    def test_use(self, traces):
        traces.append("done")


@unmagic_tester
def test_class_and_session_scope(pytester):
    @get_source
    def test_py():
        from unmagic import fixture, pytest_request, use

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture(scope="class")
        @use(pytest_request, ss_tracer)
        def cls_fix(request, traces):
            name = request.cls.__name__[-1]
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

    pytester.makepyfile(test_py)
    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        "* x1 X-a X-x2 x3 X-z y1 Y-a Y-y2 y3 Y-z",
    ])
    result.assert_outcomes(passed=6)


@unmagic_tester
def test_module_scope(pytester):
    @get_source
    def fix_py():
        from unmagic import fixture, pytest_request, use

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture(scope="module")
        @use(ss_tracer, pytest_request)
        def mod_fix(traces, request):
            name = request.module.__name__[-4:]
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

    pytester.makepyfile(fix=fix_py, test_mod1=mod1_py, test_mod2=mod2_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        "* x1 mod1-a mod1-x2 x3 mod1-z y1 mod2-a mod2-y2 y3 mod2-z",
    ])
    result.assert_outcomes(passed=6)


@unmagic_tester
def test_package_scope(pytester):
    @get_source
    def fix_py():
        from unmagic import fixture

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("\n", " ".join(traces))

    @get_source
    def init_py():
        from unmagic import fixture, use
        from fix import ss_tracer

        @fixture(scope="package")
        @use(ss_tracer)
        def pkg_fix(traces, request):
            name = request.node.nodeid.replace("/", ".")
            traces.append(f"{name}-a")
            yield
            traces.append(f"{name}-z")

    @get_source
    def mod_py():
        from unmagic import fixture, use
        from fix import ss_tracer
        from . import pkg_fix

        @fixture(scope="module")
        @use(pkg_fix)
        def modname():
            yield __name__.rsplit(".", 1)[-1].replace("test_mod", "m")

        @use(ss_tracer, modname)
        def test_one(tr, mod):
            tr.append(f"{mod}.t1")

        @use(ss_tracer, modname)
        def test_two(tr, mod):
            tr.append(f"{mod}.t2")

    (pytester.path / "pkg/sub").mkdir(parents=True)
    (pytester.path / "pkg/sub/__init__.py").write_text(init_py)
    (pytester.path / "pkg/sub/test_mod0.py").write_text(mod_py)

    (pytester.path / "pkg/__init__.py").write_text(init_py)
    (pytester.path / "pkg/test_mod1.py").write_text(mod_py)
    (pytester.path / "pkg/test_mod2.py").write_text(mod_py)

    (pytester.path / "pkg/up").mkdir()
    (pytester.path / "pkg/up/__init__.py").write_text(init_py)
    (pytester.path / "pkg/up/test_mod3.py").write_text(mod_py)

    (pytester.path / "fix.py").write_text(fix_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        " pkg.sub-a m0.t1 m0.t2 pkg.sub-z"
        " pkg-a m1.t1 m1.t2 m2.t1 m2.t2 pkg.up-a m3.t1 m3.t2 pkg.up-z pkg-z"
    ])
    result.assert_outcomes(passed=8)


@unmagic_tester
def test_fixture_autouse(pytester):

    @get_source
    def fix_py():
        from unmagic import fixture, pytest_request, use

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture(scope="module", autouse=True)
        @use(ss_tracer, pytest_request)
        def mod_fix(traces, request):
            name = request.module.__name__[-4:]
            traces.append(f"{name}-a")
            yield name
            traces.append(f"{name}-z")

    @get_source
    def mod_py():
        from unmagic import use
        from fix import ss_tracer

        @use(ss_tracer)
        def test_one(tr):
            tr.append("x1")

        @use(ss_tracer)
        def test_two(tr):
            tr.append("x2")

        @use(ss_tracer)
        def test_three(tr):
            tr.append("x3")

    pytester.makepyfile(fix=fix_py, test_mod1=mod_py, test_mod2=mod_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        "* mod1-a x1 x2 x3 mod1-z mod2-a x1 x2 x3 mod2-z",
    ])
    result.assert_outcomes(passed=6)


@unmagic_tester
def test_setup_function(pytester):
    @get_source
    def test_py():
        from unmagic import fixture, pytest_request, use

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture
        @use(ss_tracer, pytest_request)
        def fun_fix(traces, request):
            name = f"t{request.function.__name__[-1]}"
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

    pytester.makepyfile(test_py)
    result = pytester.runpytest("-sl", "--tb=long")
    result.stdout.fnmatch_lines([
        "* t0-a sf x0 t0-z t1-a sf x1 t1-z t2-a sf x2-t2 t2-z",
    ])
    result.assert_outcomes(passed=3)
