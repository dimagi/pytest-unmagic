import pytest

from unmagic import autouse, fixture, use
from .util import get_source, unmagic_tester


@unmagic_tester
def test_autouse_module_fixture(pytester):
    @get_source
    def test_py():
        from unmagic import autouse, fixture, use

        def test_one():
            pass

        def test_two():
            pass

        def test_three():
            pass

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("\n", " ".join(traces))

        @autouse(__file__)
        @fixture
        @use(ss_tracer)
        def test_name(tr, request):
            name = request.node.name.replace("test_", "")
            yield
            tr.append(name)

    pytester.makepyfile(test_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        " one two three"
    ])
    result.assert_outcomes(passed=3)


@unmagic_tester
def test_autouse_package_fixture(pytester):
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
        from unmagic import autouse, fixture, use
        from fix import ss_tracer

        @fixture(scope="package")
        @use(ss_tracer)
        def pkg_fix(traces, request):
            name = request.node.nodeid.replace("/", ".")
            traces.append(f"{name}-a")
            yield
            traces.append(f"{name}-z")

        autouse(pkg_fix, __file__)

    @get_source
    def mod_py():
        from unmagic import fixture, use
        from fix import ss_tracer

        @fixture
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

    (pytester.path / "test_mod4.py").write_text(mod_py)
    (pytester.path / "fix.py").write_text(fix_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        " pkg-a"
        " pkg.sub-a m0.t1 m0.t2 pkg.sub-z"
        " m1.t1 m1.t2 m2.t1 m2.t2"
        " pkg.up-a m3.t1 m3.t2 pkg.up-z"
        " pkg-z"
        " m4.t1 m4.t2"
    ])
    result.assert_outcomes(passed=10)


@unmagic_tester
def test_autouse_conftest_fixture(pytester):

    @get_source
    def test_py():
        from unmagic import use
        from conftest import ss_tracer

        @use(ss_tracer)
        def test_one(tr):
            tr.append("t1")

        @use(ss_tracer)
        def test_two(tr):
            tr.append("t2")

    pytester.makepyfile(conftest=plug_py, test_it=test_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([" a t1 z a t2 z"])
    result.assert_outcomes(passed=2)


@unmagic_tester
def test_autouse_plugin_fixture(pytester):

    @get_source
    def test_py():
        from unmagic import use
        from plug import ss_tracer

        @use(ss_tracer)
        def test_one(tr):
            tr.append("t1")

        @use(ss_tracer)
        def test_two(tr):
            tr.append("t2")

    pytester.makeini('[pytest]\npythonpath = .\n')
    pytester.makepyfile(plug=plug_py, test_it=test_py)

    result = pytester.runpytest("-s", "-pplug")
    result.stdout.fnmatch_lines([" a t1 z a t2 z"])
    result.assert_outcomes(passed=2)


@get_source
def plug_py():
    from unmagic import fixture, use

    @fixture(scope="session")
    def ss_tracer():
        traces = []
        yield traces
        print("\n", " ".join(traces))

    @fixture(autouse=True)
    @use(ss_tracer)
    def autofix(traces, request):
        traces.append("a")
        yield
        traces.append("z")


@fixture
def fun():
    yield


@pytest.mark.parametrize("value", [None, lambda: None, fun])
def test_autouse_decorator_error(value):
    with pytest.raises(ValueError, match="requires a location"):
        autouse(value)
