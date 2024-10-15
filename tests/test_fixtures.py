from contextlib import contextmanager
from unittest.mock import patch

import pytest
from _pytest.outcomes import Failed

from unmagic import _api, fence, fixture, pytest_request, use
from unmagic.fixtures import UnmagicFixture

from .util import get_source, unmagic_tester


@fixture
def tracer():
    yield []


@fixture
@tracer
def fix():
    traces = tracer()
    traces.append("fixing...")
    yield "fixed value"
    traces.append("fix done")


@tracer
@fixture
def check_done():
    traces = tracer()
    yield
    assert traces[-1].endswith("done")


@use(check_done, fix, tracer)
def test_unmagic_fixture():
    assert fix() == "fixed value"
    assert tracer() == ["fixing..."]
    assert test_unmagic_fixture.unmagic_fixtures == [check_done, fix, tracer]


@pytest.mark.parametrize("p1, p2", [(1, 2), (2, 3)])
@check_done
def test_params(p1, p2):
    assert p1 + 1 == p2
    tracer().append("done")


@check_done
@fix
def test_unmagic_fixture_as_decorator():
    assert tracer() == ["fixing..."]
    assert fix() == "fixed value"
    assert test_unmagic_fixture_as_decorator.unmagic_fixtures \
        == [tracer, fix, check_done]


def test_use_generator_should_return_generator():
    @fix
    def gen():
        yield
    assert _api.is_generator(gen)


class Thing:
    x = 0
    y = 4000
    z = -1


@fixture
@use(
    patch.object(Thing, "x", 2),
    patch.object(Thing, "z", -2),
)
def patch_things():
    yield (Thing.x, Thing.y, Thing.z)


@patch.object(Thing, "y")
def test_patch_with_unmagic_fixture(mock):
    assert patch_things() == (2, mock, -2)


@contextmanager
def plain_context():
    yield "other"


def test_plain_contextmanager_fixture():
    other_fixture = UnmagicFixture.create(plain_context)
    assert other_fixture() == "other"


def test_module_is_fenced():
    assert fence.is_fenced(test_module_is_fenced)


def test_use_magic_fixture():
    cap = pytest_request().getfixturevalue("capsys")
    print("hello")
    captured = cap.readouterr()
    assert captured.out == "hello\n"


@fixture
def broken_fix():
    return "nope"


def test_malformed_unmagic_fixture():
    @broken_fix
    def test():
        assert 0, "should not get here"

    with pytest.raises(Failed, match="fixture 'broken_fix' does not yield"):
        test()


def test_malformed_unmagic_fixture_get_value():
    with pytest.raises(TypeError, match="fixture 'broken_fix' does not yield"):
        broken_fix()


def test_fixture_is_not_a_test():
    @get_source
    def test_py():
        from unmagic import fixture

        @fixture(scope="session")
        def test_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        def test_thing():
            test_tracer().append("x0")

    pytester = unmagic_tester()
    pytester.makepyfile(test_py)
    result = pytester.runpytest("-sv")
    result.stdout.fnmatch_lines([
        "* x0",
    ])
    result.assert_outcomes(passed=1)


def test_improper_fixture_dependency():
    @get_source
    def test_py():
        from unmagic import fixture

        @fixture
        def tracer():
            yield []

        @fixture(scope="class")
        def class_tracer():
            traces = tracer()
            yield traces
            print("", " ".join(traces))

        @class_tracer
        def test():
            assert 0, "should not get here"

    pytester = unmagic_tester()
    pytester.makepyfile(test_py)
    result = pytester.runpytest("-sv", "--setup-show")
    result.stdout.fnmatch_lines([
        "* tried to access the function scoped fixture tracer "
        "with a class scoped request *"
    ])
    result.assert_outcomes(failed=1)


@fixture(scope="module")
def module_request():
    yield pytest_request()


def test_fixture_request():
    assert pytest_request().scope == "function"
    assert module_request().scope == "module"


class TestMethodUse:

    @check_done
    def test_use(self):
        tracer().append("done")


def test_class_and_session_scope():
    @get_source
    def test_py():
        from unmagic import fixture, pytest_request

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture(scope="class")
        def cls_fix():
            name = pytest_request().cls.__name__[-1]
            traces = ss_tracer()
            traces.append(f"{name}-a")
            yield name
            traces.append(f"{name}-z")

        class TestX:
            def test_one(self):
                ss_tracer().append("x1")

            def test_two(self):
                ss_tracer().append(f"{cls_fix()}-x2")

            def test_three(self):
                ss_tracer().append("x3")

        class TestY:
            def test_one(self):
                ss_tracer().append("y1")

            def test_two(self):
                ss_tracer().append(f"{cls_fix()}-y2")

            def test_three(self):
                ss_tracer().append("y3")

    pytester = unmagic_tester()
    pytester.makepyfile(test_py)
    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        "* x1 X-a X-x2 x3 X-z y1 Y-a Y-y2 y3 Y-z",
    ])
    result.assert_outcomes(passed=6)


def test_fixture_as_class_decorator():
    @get_source
    def test_py():
        from unittest import TestCase
        from unmagic import fixture, pytest_request

        traces = []

        @fixture(scope="session")
        def ss_tracer():
            yield traces
            print("", " ".join(traces))

        @fixture(scope="class")
        @ss_tracer
        def cls_fix():
            name = pytest_request().cls.__name__[-1]
            traces.append(f"{name}-a")
            yield name
            traces.append(f"{name}-z")

        @cls_fix
        class TestX:
            def test_one(self):
                traces.append("X1")

            def test_two(self):
                traces.append("X2")

            def test_three(self):
                traces.append("X3")

        @cls_fix
        class TestY(TestCase):
            def test_one(self):
                traces.append("Y1")

            def test_two(self):
                traces.append("Y2")

            def test_three(self):
                traces.append("Y3")

    pytester = unmagic_tester()
    pytester.makepyfile(test_py)
    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        "* X-a X1 X2 X3 X-z Y-a Y1 Y3 Y2 Y-z",
    ])
    result.assert_outcomes(passed=6)


def test_non_function_scoped_contextmanager_fixture():
    @get_source
    def test_py():
        from contextlib import contextmanager
        from unmagic.fixtures import UnmagicFixture

        traces = []

        @contextmanager
        def context():
            traces.append("setup")
            yield
            traces.append("teardown")
            print("", " ".join(traces))

        @UnmagicFixture.create(context, scope="class")
        class Tests:
            def test_one(self):
                traces.append("1")

            def test_two(self):
                traces.append("2")

            def test_three(self):
                traces.append("3")

    pytester = unmagic_tester()
    pytester.makepyfile(test_py)
    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines(["* setup 1 2 3 teardown"])
    result.assert_outcomes(passed=3)


def test_module_scope():
    @get_source
    def fix_py():
        from unmagic import fixture, pytest_request

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture(scope="module")
        def mod_fix():
            name = pytest_request().module.__name__[-4:]
            traces = ss_tracer()
            traces.append(f"{name}-a")
            yield name
            traces.append(f"{name}-z")

    @get_source
    def mod1_py():
        from fix import ss_tracer, mod_fix

        def test_one():
            ss_tracer().append("x1")

        def test_two():
            ss_tracer().append(f"{mod_fix()}-x2")

        def test_three():
            ss_tracer().append("x3")

    @get_source
    def mod2_py():
        from fix import ss_tracer, mod_fix

        def test_one():
            ss_tracer().append("y1")

        def test_two():
            ss_tracer().append(f"{mod_fix()}-y2")

        def test_three():
            ss_tracer().append("y3")

    pytester = unmagic_tester()
    pytester.makepyfile(fix=fix_py, test_mod1=mod1_py, test_mod2=mod2_py)
    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        "* x1 mod1-a mod1-x2 x3 mod1-z y1 mod2-a mod2-y2 y3 mod2-z",
    ])
    result.assert_outcomes(passed=6)


def test_package_scope():
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
        from unmagic import fixture, pytest_request
        from fix import ss_tracer

        @fixture(scope="package")
        def pkg_fix():
            name = pytest_request().node.nodeid.replace("/", ".")
            traces = ss_tracer()
            traces.append(f"{name}-a")
            yield
            traces.append(f"{name}-z")

    @get_source
    def mod_py():
        from unmagic import fixture
        from fix import ss_tracer
        from . import pkg_fix

        @fixture(scope="module")
        @pkg_fix
        def modname():
            yield __name__.rsplit(".", 1)[-1].replace("test_mod", "m")

        def test_one():
            ss_tracer().append(f"{modname()}.t1")

        def test_two():
            ss_tracer().append(f"{modname()}.t2")

    pytester = unmagic_tester()
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


def test_fixture_autouse():

    @get_source
    def fix_py():
        from unmagic import fixture, pytest_request

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture(scope="module", autouse=True)
        def mod_fix():
            name = pytest_request().module.__name__[-4:]
            traces = ss_tracer()
            traces.append(f"{name}-a")
            yield name
            traces.append(f"{name}-z")

    @get_source
    def mod_py():
        from fix import ss_tracer

        def test_one():
            ss_tracer().append("x1")

        def test_two():
            ss_tracer().append("x2")

        def test_three():
            ss_tracer().append("x3")

    pytester = unmagic_tester()
    pytester.makepyfile(fix=fix_py, test_mod1=mod_py, test_mod2=mod_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        "* mod1-a x1 x2 x3 mod1-z mod2-a x1 x2 x3 mod2-z",
    ])
    result.assert_outcomes(passed=6)


def test_setup_function():
    @get_source
    def test_py():
        from unmagic import fixture, pytest_request

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("", " ".join(traces))

        @fixture
        def fun_fix():
            name = f"t{pytest_request().function.__name__[-1]}"
            traces = ss_tracer()
            traces.append(f"{name}-a")
            yield name
            traces.append(f"{name}-z")

        @fun_fix
        def setup_function():
            ss_tracer().append("sf")

        def test_x0():
            ss_tracer().append("x0")

        def test_x1():
            ss_tracer().append("x1")

        def test_x2():
            ss_tracer().append(f"x2-{fun_fix()}")

    pytester = unmagic_tester()
    pytester.makepyfile(test_py)
    result = pytester.runpytest("-sl", "--tb=long")
    result.stdout.fnmatch_lines([
        "* t0-a sf x0 t0-z t1-a sf x1 t1-z t2-a sf x2-t2 t2-z",
    ])
    result.assert_outcomes(passed=3)


class TestFixturesOption:

    def test_basic(self):
        @get_source
        def test_py():
            from unmagic import fixture

            @fixture
            def fix():
                "A fixture"
                yield

            @fix
            def test():
                pass

        pytester = unmagic_tester()
        pytester.makepyfile(test_py)
        result = pytester.runpytest("--fixtures")
        result.stdout.re_match_lines([
            r"-* fixtures defined from test_basic -*",
            r"fix -- test_basic.py:4",
            r" +A fixture",
        ])
        result.assert_outcomes()

    def test_fixture_uses_fixture(self):
        @get_source
        def test_py():
            from unmagic import fixture

            @fixture
            def first():
                "First fixture"
                yield

            @first  # important: @use applied after @fixture
            @fixture
            def second():
                "Second fixture"
                yield

            @second
            def test():
                pass

        pytester = unmagic_tester()
        pytester.makepyfile(test_py)
        result = pytester.runpytest("--fixtures")
        result.stdout.re_match_lines([
            r"-* fixtures defined from test_fixture_uses_fixture -*",
            r"second -- test_fixture_uses_fixture.py:9",
            r" +Second fixture",
        ])
        result.assert_outcomes()

    def test_use_magic_fixture(self):
        @get_source
        def test_py():
            from _pytest.capture import capsys
            from unmagic import use

            @use(capsys)
            def test():
                pass

        pytester = unmagic_tester()
        pytester.makepyfile(test_py)
        result = pytester.runpytest("--fixtures")
        result.stdout.re_match_lines([
            r"capsys -- \.{3}/_pytest/capture.py:\d+",
            r" +Enable text capturing .+",
        ])
        result.assert_outcomes()

    def test_use_contextmanager(self):
        @get_source
        def test_py():
            from contextlib import contextmanager
            from unmagic import use

            @contextmanager
            def plain_jane():
                """Plain Jane"""
                yield

            @use(plain_jane)
            def test():
                pass

        pytester = unmagic_tester()
        pytester.makepyfile(test_py)
        result = pytester.runpytest("--fixtures")
        result.stdout.re_match_lines([
            r"-* fixtures defined from test_use_contextmanager -*",
            r"plain_jane -- test_use_contextmanager.py:\d+",
            r" +Plain Jane",
        ])
        result.assert_outcomes()

    def test_use_patch(self):
        @get_source
        def test_py():
            from unittest.mock import patch
            from unmagic import use

            @use(patch.object(use, "x", 2))
            def test():
                pass

        pytester = unmagic_tester()
        pytester.makepyfile(test_py)
        result = pytester.runpytest("--fixtures")
        result.stdout.re_match_lines([
            r"-* fixtures defined from unittest.mock -*",
            r"<patch use\.x> -- .+/unittest/mock\.py:\d+",
        ])
        result.assert_outcomes()


class TestUnmagicFixtureId:

    @fixture
    def one():
        pass

    @fixture
    def two():
        pass

    def test_str(self):
        assert str(self.one._id) == "one"

    def test_repr(self):
        assert repr(self.one._id).startswith("<one ")

    def test_equality(self):
        assert self.one._id == self.one._id
        assert self.one._id != self.two._id
        assert self.one._id != "one"
        assert "one" != self.one._id

    def test_hash(self):
        data = {self.one._id: self.one, "one": object()}
        assert len(data) == 2
        assert data[self.one._id] is self.one
        assert data["one"] is not self.one
